"""Outbound alert notifications — Slack incoming webhooks or any HTTPS webhook.

A user configures one webhook URL. Watchtower regression/improved alerts are
POSTed to it (Slack-formatted if it's a Slack hook, JSON otherwise). Sends run
in a daemon thread so they never block the scheduler or API.
"""
import json
import sqlite3
import threading
import datetime as dt

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import DB_PATH, get_current_user

router = APIRouter(prefix="/settings", tags=["notifications"])


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS webhooks (
                user_id    INTEGER PRIMARY KEY,
                url        TEXT NOT NULL DEFAULT '',
                enabled    INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL
            )"""
        )


def get_webhook(user_id: int):
    with _db() as conn:
        return conn.execute("SELECT * FROM webhooks WHERE user_id = ?", (user_id,)).fetchone()


def _build_body(url: str, domain: str, atype: str, message: str, from_score, to_score) -> dict:
    if "hooks.slack.com" in url or "webhook.office.com" in url:  # Slack / Teams accept {text}
        emoji = "🔴" if atype == "regression" else "🟢" if atype == "improved" else "🔔"
        return {"text": f"{emoji} *ConsentGuard* — `{domain}`\n{message}"}
    return {
        "source": "consentguard",
        "event": atype,
        "domain": domain,
        "message": message,
        "from_score": from_score,
        "to_score": to_score,
        "at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def _post(url: str, body: dict) -> None:
    try:
        requests.post(url, json=body, timeout=6)
    except Exception:  # noqa: BLE001
        pass


def send_alert(user_id: int, domain: str, atype: str, message: str, from_score=None, to_score=None) -> None:
    """Fire-and-forget: dispatch the alert to the user's webhook in a background thread."""
    row = get_webhook(user_id)
    if not row or not row["enabled"] or not (row["url"] or "").strip():
        return
    body = _build_body(row["url"], domain, atype, message, from_score, to_score)
    threading.Thread(target=_post, args=(row["url"], body), daemon=True).start()


# ─────────────────────────── API ───────────────────────────
class WebhookIn(BaseModel):
    url: str = Field("", max_length=500)
    enabled: bool = True


@router.get("/webhook")
def get_wh(user: dict = Depends(get_current_user)) -> dict:
    row = get_webhook(user["id"])
    return {"url": row["url"] if row else "", "enabled": bool(row["enabled"]) if row else True}


@router.put("/webhook")
def put_wh(body: WebhookIn, user: dict = Depends(get_current_user)) -> dict:
    url = body.url.strip()
    if url and not url.startswith("https://"):
        raise HTTPException(status_code=422, detail="Webhook URL must start with https://")
    with _db() as conn:
        conn.execute(
            """INSERT INTO webhooks (user_id, url, enabled, updated_at) VALUES (?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET url=excluded.url, enabled=excluded.enabled, updated_at=excluded.updated_at""",
            (user["id"], url, 1 if body.enabled else 0, dt.datetime.now(dt.timezone.utc).isoformat()),
        )
    return {"url": url, "enabled": body.enabled}


@router.post("/webhook/test")
def test_wh(user: dict = Depends(get_current_user)) -> dict:
    row = get_webhook(user["id"])
    if not row or not (row["url"] or "").strip():
        raise HTTPException(status_code=400, detail="Save a webhook URL first.")
    body = _build_body(row["url"], "example.com", "regression",
                       "Test alert — new tracker: criteo.com · score B→D", 82, 58)
    try:
        r = requests.post(row["url"], json=body, timeout=8)
    except requests.RequestException as exc:
        raise HTTPException(status_code=400, detail=f"Could not reach the webhook: {exc}")
    if r.status_code >= 300:
        raise HTTPException(status_code=400, detail=f"Webhook responded with HTTP {r.status_code}.")
    return {"ok": True, "status": r.status_code}
