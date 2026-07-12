"""Per-user scan history storage (SQLite), reusing the auth DB + JWT.

Frontend runs a scan via the public /scan endpoint, then POSTs the summary +
full payload here (authenticated) so it shows up in the user's dashboard.
"""
import json
import sqlite3
import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import DB_PATH, get_current_user

router = APIRouter(prefix="/scans", tags=["scans"])


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER NOT NULL,
                url              TEXT NOT NULL,
                domain           TEXT NOT NULL,
                score            INTEGER NOT NULL DEFAULT 0,
                grade            TEXT NOT NULL DEFAULT 'F',
                consent_platform TEXT,
                tracker_count    INTEGER NOT NULL DEFAULT 0,
                undeclared_count INTEGER NOT NULL DEFAULT 0,
                fine_range       TEXT,
                payload          TEXT NOT NULL,
                created_at       TEXT NOT NULL
            )
            """
        )


class ScanIn(BaseModel):
    url: str = Field(..., max_length=500)
    domain: str = Field("", max_length=253)
    score: int = 0
    grade: str = Field("F", max_length=2)
    consent_platform: str | None = None
    tracker_count: int = 0
    undeclared_count: int = 0
    fine_range: str | None = None
    payload: dict = Field(default_factory=dict)


def _summary(row) -> dict:
    return {
        "id": row["id"],
        "url": row["url"],
        "domain": row["domain"],
        "score": row["score"],
        "grade": row["grade"],
        "consent_platform": row["consent_platform"],
        "tracker_count": row["tracker_count"],
        "undeclared_count": row["undeclared_count"],
        "fine_range": row["fine_range"],
        "created_at": row["created_at"],
    }


@router.post("")
def create_scan(body: ScanIn, user: dict = Depends(get_current_user)) -> dict:
    domain = body.domain or body.url.replace("https://", "").replace("http://", "").split("/")[0]
    with _db() as conn:
        cur = conn.execute(
            """INSERT INTO scans
               (user_id, url, domain, score, grade, consent_platform,
                tracker_count, undeclared_count, fine_range, payload, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                user["id"], body.url, domain, body.score, body.grade, body.consent_platform,
                body.tracker_count, body.undeclared_count, body.fine_range,
                json.dumps(body.payload), dt.datetime.now(dt.timezone.utc).isoformat(),
            ),
        )
        row = conn.execute("SELECT * FROM scans WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _summary(row)


@router.get("")
def list_scans(user: dict = Depends(get_current_user)) -> dict:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM scans WHERE user_id = ? ORDER BY id DESC", (user["id"],)
        ).fetchall()
    return {"scans": [_summary(r) for r in rows]}


@router.get("/{scan_id}")
def get_scan(scan_id: int, user: dict = Depends(get_current_user)) -> dict:
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM scans WHERE id = ? AND user_id = ?", (scan_id, user["id"])
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Scan not found.")
    data = _summary(row)
    try:
        data["payload"] = json.loads(row["payload"])
    except Exception:
        data["payload"] = {}
    return data


@router.delete("/{scan_id}")
def delete_scan(scan_id: int, user: dict = Depends(get_current_user)) -> dict:
    with _db() as conn:
        cur = conn.execute(
            "DELETE FROM scans WHERE id = ? AND user_id = ?", (scan_id, user["id"])
        )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Scan not found.")
    return {"deleted": scan_id}
