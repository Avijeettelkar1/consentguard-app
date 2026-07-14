"""Watchtower — continuous compliance monitoring.

Users add domains to a watchlist; a background scheduler re-scans each domain on
its interval, records the run, diffs it against the previous run, and raises a
regression alert when the compliance score drops or new trackers appear.

Storage reuses the auth SQLite DB. Scans use the same real pipeline as /scan.
"""
import os
import json
import asyncio
import sqlite3
import datetime as dt
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import DB_PATH, get_current_user

router = APIRouter(prefix="/watch", tags=["watchtower"])

POLL_SECONDS = int(os.getenv("WATCH_POLL_SECONDS", "30"))       # how often the scheduler wakes
DEFAULT_INTERVAL_HOURS = int(os.getenv("WATCH_INTERVAL_HOURS", "12"))
MAX_WATCHES = int(os.getenv("WATCH_MAX", "25"))
TREND_POINTS = 12


# ─────────────────────────── storage ───────────────────────────
def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _iso(d: dt.datetime) -> str:
    return d.isoformat()


def init_db() -> None:
    with _db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS watches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                url TEXT NOT NULL,
                domain TEXT NOT NULL,
                interval_hours INTEGER NOT NULL DEFAULT 12,
                status TEXT NOT NULL DEFAULT 'pending',
                last_score INTEGER,
                last_grade TEXT,
                consent_platform TEXT,
                undeclared_count INTEGER DEFAULT 0,
                error TEXT,
                last_checked_at TEXT,
                next_check_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS monitor_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watch_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                score INTEGER NOT NULL DEFAULT 0,
                grade TEXT NOT NULL DEFAULT 'F',
                undeclared_count INTEGER NOT NULL DEFAULT 0,
                tracker_domains TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                watch_id INTEGER,
                domain TEXT NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                from_score INTEGER,
                to_score INTEGER,
                read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )"""
        )


# ─────────────────────── scoring (mirror of frontend score.js) ───────────────────────
def _score(undeclared: int, needs_review: int, clicked_reject) -> tuple[int, str]:
    if undeclared == 0:
        score = 88 if needs_review > 0 else 100
    else:
        score = 74 - (undeclared - 1) * 7 - needs_review * 2 - (8 if clicked_reject is False else 0)
        score = max(5, min(74, score))
    grade = 'A' if score >= 90 else 'B' if score >= 80 else 'C' if score >= 65 else 'D' if score >= 50 else 'F'
    return score, grade


def _scan_and_summarize(url: str) -> dict:
    """Run the real pipeline and return a compliance summary. Raises on failure."""
    if os.getenv("MOCK", "false").lower() == "true":
        import hashlib
        h = int(hashlib.sha256(url.encode()).hexdigest(), 16)
        n = h % 6
        domains = [f"tracker{i}.adnetwork.com" for i in range(n)]
        score, grade = _score(n, 0, True)
        return {"score": score, "grade": grade, "undeclared_count": n,
                "undeclared_domains": domains, "consent_platform": "OneTrust" if n else None}

    from scanner import run_scan
    from analyzer import find_violations, fetch_cookie_policy, analyze_violations
    from tag_audit import audit_tags, filter_domain_violations_with_tag_audit

    scan_data = run_scan(url)
    tracker_hits = find_violations(scan_data.get("after", []))
    policy_text = fetch_cookie_policy(scan_data.get("cookie_policy_url"))
    analysis = analyze_violations(tracker_hits, policy_text, scan_data.get("page_html_for_fallback", ""))
    tag_audit = audit_tags(scan_data)
    analysis["violations"] = filter_domain_violations_with_tag_audit(analysis.get("violations", []), tag_audit)

    undeclared = [v for v in analysis["violations"] if not v.get("declared") and not v.get("needs_review")]
    needs_review = [v for v in analysis["violations"] if v.get("needs_review")]
    undeclared_domains = sorted({v.get("domain") for v in undeclared if v.get("domain")})
    score, grade = _score(len(undeclared_domains), len(needs_review), scan_data.get("clicked_reject"))
    return {
        "score": score, "grade": grade,
        "undeclared_count": len(undeclared_domains),
        "undeclared_domains": undeclared_domains,
        "consent_platform": scan_data.get("consent_platform"),
    }


# ─────────────────────── run recording + diff/alerts ───────────────────────
def _record_run(watch: dict, summ: dict) -> None:
    now = _now()
    with _db() as conn:
        prev = conn.execute(
            "SELECT * FROM monitor_runs WHERE watch_id = ? ORDER BY id DESC LIMIT 1", (watch["id"],)
        ).fetchone()

        conn.execute(
            """INSERT INTO monitor_runs (watch_id, user_id, score, grade, undeclared_count, tracker_domains, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (watch["id"], watch["user_id"], summ["score"], summ["grade"], summ["undeclared_count"],
             json.dumps(summ["undeclared_domains"]), _iso(now)),
        )
        next_check = now + dt.timedelta(hours=watch["interval_hours"])
        status = "ok" if summ["undeclared_count"] == 0 else "alert"
        conn.execute(
            """UPDATE watches SET status=?, last_score=?, last_grade=?, consent_platform=?,
               undeclared_count=?, error=NULL, last_checked_at=?, next_check_at=? WHERE id=?""",
            (status, summ["score"], summ["grade"], summ.get("consent_platform"),
             summ["undeclared_count"], _iso(now), _iso(next_check), watch["id"]),
        )

        if prev is not None:
            prev_domains = set(json.loads(prev["tracker_domains"] or "[]"))
            cur_domains = set(summ["undeclared_domains"])
            added = sorted(cur_domains - prev_domains)
            dropped = summ["score"] < prev["score"]
            if added or dropped:
                if added:
                    extra = f" +{len(added) - 2} more" if len(added) > 2 else ""
                    msg = f"New tracker{'s' if len(added) > 1 else ''}: {', '.join(added[:2])}{extra} · score {prev['grade']}→{summ['grade']}"
                else:
                    msg = f"Compliance slipped · score {prev['grade']}→{summ['grade']}"
                _add_alert(conn, watch, "regression", msg, prev["score"], summ["score"])
            elif summ["score"] > prev["score"]:
                _add_alert(conn, watch, "improved", f"Improved · score {prev['grade']}→{summ['grade']}", prev["score"], summ["score"])


def _add_alert(conn, watch, atype, message, from_score, to_score) -> None:
    conn.execute(
        """INSERT INTO alerts (user_id, watch_id, domain, type, message, from_score, to_score, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (watch["user_id"], watch["id"], watch["domain"], atype, message, from_score, to_score, _iso(_now())),
    )
    # push to the user's Slack / webhook if configured (fire-and-forget)
    try:
        import notify
        notify.send_alert(watch["user_id"], watch["domain"], atype, message, from_score, to_score)
    except Exception:  # noqa: BLE001
        pass


def _record_error(watch: dict, err: str) -> None:
    now = _now()
    with _db() as conn:
        conn.execute(
            "UPDATE watches SET status='error', error=?, last_checked_at=?, next_check_at=? WHERE id=?",
            (err[:300], _iso(now), _iso(now + dt.timedelta(hours=watch["interval_hours"])), watch["id"]),
        )


# ─────────────────────────── scheduler ───────────────────────────
_scheduler_started = False


async def _monitor_loop() -> None:
    while True:
        try:
            with _db() as conn:
                due = conn.execute(
                    "SELECT * FROM watches WHERE next_check_at <= ? ORDER BY next_check_at ASC LIMIT 5",
                    (_iso(_now()),),
                ).fetchall()
            for row in due:
                watch = dict(row)
                try:
                    summ = await asyncio.to_thread(_scan_and_summarize, watch["url"])
                    _record_run(watch, summ)
                except Exception as exc:  # noqa: BLE001
                    _record_error(watch, str(exc))
                await asyncio.sleep(1)  # breathe between heavy scans
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(POLL_SECONDS)


def start_scheduler() -> None:
    global _scheduler_started
    if _scheduler_started or os.getenv("DISABLE_SCHEDULER"):
        return
    _scheduler_started = True
    try:
        asyncio.get_event_loop().create_task(_monitor_loop())
    except RuntimeError:
        asyncio.ensure_future(_monitor_loop())


# ─────────────────────────── API ───────────────────────────
class WatchIn(BaseModel):
    url: str = Field(..., max_length=500)
    interval_hours: int | None = Field(None, ge=1, le=168)


def _trend(conn, watch_id: int) -> list[int]:
    rows = conn.execute(
        "SELECT score FROM monitor_runs WHERE watch_id = ? ORDER BY id DESC LIMIT ?", (watch_id, TREND_POINTS)
    ).fetchall()
    return [r["score"] for r in reversed(rows)]


def _watch_public(conn, row) -> dict:
    return {
        "id": row["id"], "url": row["url"], "domain": row["domain"],
        "interval_hours": row["interval_hours"], "status": row["status"],
        "last_score": row["last_score"], "last_grade": row["last_grade"],
        "consent_platform": row["consent_platform"], "undeclared_count": row["undeclared_count"],
        "error": row["error"], "last_checked_at": row["last_checked_at"],
        "next_check_at": row["next_check_at"], "trend": _trend(conn, row["id"]),
    }


@router.get("")
def list_watches(user: dict = Depends(get_current_user)) -> dict:
    with _db() as conn:
        rows = conn.execute("SELECT * FROM watches WHERE user_id = ? ORDER BY id DESC", (user["id"],)).fetchall()
        return {"watches": [_watch_public(conn, r) for r in rows]}


@router.post("")
def add_watch(body: WatchIn, user: dict = Depends(get_current_user)) -> dict:
    raw = body.url.strip()
    if not raw.startswith(("http://", "https://")):
        raw = "https://" + raw
    host = (urlparse(raw).hostname or "").lower()
    if "." not in host:
        raise HTTPException(status_code=422, detail="Enter a valid domain to monitor.")
    with _db() as conn:
        count = conn.execute("SELECT COUNT(*) c FROM watches WHERE user_id = ?", (user["id"],)).fetchone()["c"]
        if count >= MAX_WATCHES:
            raise HTTPException(status_code=400, detail=f"You can monitor up to {MAX_WATCHES} domains.")
        dup = conn.execute("SELECT 1 FROM watches WHERE user_id = ? AND domain = ?", (user["id"], host)).fetchone()
        if dup:
            raise HTTPException(status_code=409, detail=f"You're already monitoring {host}.")
        now = _now()
        cur = conn.execute(
            """INSERT INTO watches (user_id, url, domain, interval_hours, status, next_check_at, created_at)
               VALUES (?,?,?,?,'pending',?,?)""",
            (user["id"], raw, host, body.interval_hours or DEFAULT_INTERVAL_HOURS, _iso(now), _iso(now)),
        )
        row = conn.execute("SELECT * FROM watches WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _watch_public(conn, row)


@router.post("/{watch_id}/scan")
def scan_now(watch_id: int, user: dict = Depends(get_current_user)) -> dict:
    with _db() as conn:
        row = conn.execute("SELECT 1 FROM watches WHERE id=? AND user_id=?", (watch_id, user["id"])).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Not found.")
        conn.execute("UPDATE watches SET next_check_at=?, status=CASE WHEN status='pending' THEN 'pending' ELSE status END WHERE id=?",
                     (_iso(_now()), watch_id))
    return {"queued": True}


@router.delete("/{watch_id}")
def delete_watch(watch_id: int, user: dict = Depends(get_current_user)) -> dict:
    with _db() as conn:
        cur = conn.execute("DELETE FROM watches WHERE id=? AND user_id=?", (watch_id, user["id"]))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Not found.")
        conn.execute("DELETE FROM monitor_runs WHERE watch_id=?", (watch_id,))
    return {"deleted": watch_id}


@router.get("/alerts")
def list_alerts(user: dict = Depends(get_current_user)) -> dict:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM alerts WHERE user_id = ? ORDER BY id DESC LIMIT 30", (user["id"],)
        ).fetchall()
        return {"alerts": [dict(r) for r in rows]}


@router.post("/alerts/read")
def mark_alerts_read(user: dict = Depends(get_current_user)) -> dict:
    with _db() as conn:
        conn.execute("UPDATE alerts SET read=1 WHERE user_id=?", (user["id"],))
    return {"ok": True}
