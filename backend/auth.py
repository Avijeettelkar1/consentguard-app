"""JWT authentication for ConsentGuard.

Self-contained: SQLite user store + pbkdf2 password hashing (stdlib) + PyJWT.
No external services required, so it runs anywhere the API runs.
"""
import os
import re
import hmac
import hashlib
import secrets
import sqlite3
import datetime as dt
from pathlib import Path

import jwt  # PyJWT
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

JWT_SECRET = os.getenv("JWT_SECRET", "consentguard-dev-secret-change-in-prod")
JWT_ALG = "HS256"
JWT_TTL_HOURS = int(os.getenv("JWT_TTL_HOURS", "168"))  # 7 days
DB_PATH = os.getenv("CG_DB_PATH") or str(Path(__file__).with_name("consentguard.db"))

router = APIRouter(prefix="/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=True)


# ─────────────────────────── storage ───────────────────────────
def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT UNIQUE NOT NULL,
                name          TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at    TEXT NOT NULL
            )
            """
        )


# ─────────────────────── password hashing ──────────────────────
def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 120_000)
    return f"pbkdf2_sha256$120000${salt}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        _algo, iters, salt, digest = stored.split("$")
        expected = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iters))
        return hmac.compare_digest(expected.hex(), digest)
    except Exception:
        return False


# ───────────────────────────── jwt ─────────────────────────────
def _make_token(user_id: int, email: str) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "exp": now + dt.timedelta(hours=JWT_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def get_current_user(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> dict:
    try:
        payload = jwt.decode(cred.credentials, JWT_SECRET, algorithms=[JWT_ALG])
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")

    with _db() as conn:
        row = conn.execute("SELECT id, email, name, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="User no longer exists.")
    return dict(row)


# ──────────────────────────── models ───────────────────────────
class SignupReq(BaseModel):
    email: str = Field(..., max_length=200)
    password: str = Field(..., min_length=8, max_length=200)
    name: str = Field("", max_length=120)

    @field_validator("email")
    @classmethod
    def _valid_email(cls, v: str) -> str:
        if not _EMAIL_RE.match(v.strip()):
            raise ValueError("Enter a valid email address.")
        return v


class LoginReq(BaseModel):
    email: str = Field(..., max_length=200)
    password: str = Field(..., min_length=1, max_length=200)


def _user_public(row) -> dict:
    return {"id": row["id"], "email": row["email"], "name": row["name"]}


# ──────────────────────────── routes ───────────────────────────
@router.post("/signup")
def signup(req: SignupReq) -> dict:
    email = req.email.lower().strip()
    name = req.name.strip() or email.split("@")[0]
    with _db() as conn:
        exists = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        if exists:
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        cur = conn.execute(
            "INSERT INTO users (email, name, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (email, name, _hash_password(req.password), dt.datetime.now(dt.timezone.utc).isoformat()),
        )
        user_id = cur.lastrowid
        row = conn.execute("SELECT id, email, name FROM users WHERE id = ?", (user_id,)).fetchone()
    return {"access_token": _make_token(user_id, email), "token_type": "bearer", "user": _user_public(row)}


@router.post("/login")
def login(req: LoginReq) -> dict:
    email = req.email.lower().strip()
    with _db() as conn:
        row = conn.execute("SELECT id, email, name, password_hash FROM users WHERE email = ?", (email,)).fetchone()
    if row is None or not _verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return {"access_token": _make_token(row["id"], email), "token_type": "bearer", "user": _user_public(row)}


@router.get("/me")
def me(user: dict = Depends(get_current_user)) -> dict:
    return {"user": {"id": user["id"], "email": user["email"], "name": user["name"]}}
