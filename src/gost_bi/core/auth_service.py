"""
GOST BI Auth Service — local + ESIA authentication.

Provides:
- Login with login/password (bcrypt) → JWT
- Login with ESIA OAuth2 → JWT
- User registration (admin only)
- Token refresh
- Audit logging
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from sqlalchemy import create_engine, text

logger = logging.getLogger("gost_bi.auth.service")

JWT_SECRET = os.environ.get("JWT_SECRET", "gost-bi-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
DB_URL = os.environ.get("DATABASE_URL", "postgresql://gostbi:gostbi@localhost:5432/gostbi")


def _get_engine():
    return create_engine(DB_URL, connect_args={"connect_timeout": 3})


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_jwt(user_id: int, login: str, full_name: str, role: str, org: str = "") -> str:
    payload = {
        "sub": str(user_id),
        "login": login,
        "name": full_name,
        "role": role,
        "org": org,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def _log_audit(user_id: int | None, login: str, action: str, detail: str = "", ip: str = "") -> None:
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO audit_log (user_id, login, action, detail, ip_address) "
                    "VALUES (:uid, :login, :action, :detail, :ip)"
                ),
                {"uid": user_id, "login": login, "action": action, "detail": detail, "ip": ip},
            )
            conn.commit()
    except Exception as exc:
        logger.warning(f"Audit log failed: {exc}")


def authenticate(login: str, password: str, ip_address: str = "") -> dict[str, Any] | None:
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT id, login, password_hash, full_name, role, organization, is_active FROM users WHERE login = :login"),
                {"login": login},
            ).fetchone()

            if not row:
                _log_audit(None, login, "LOGIN_FAILED", "User not found", ip_address)
                return None

            user_id, db_login, pw_hash, full_name, role, org, is_active = row

            if not is_active:
                _log_audit(user_id, login, "LOGIN_BLOCKED", "Account inactive", ip_address)
                return None

            if not verify_password(password, pw_hash):
                _log_audit(user_id, login, "LOGIN_FAILED", "Wrong password", ip_address)
                return None

            token = create_jwt(user_id, db_login, full_name, role, org)

            conn.execute(
                text("UPDATE users SET last_login = :now WHERE id = :uid"),
                {"now": datetime.now(timezone.utc), "uid": user_id},
            )
            conn.commit()

            _log_audit(user_id, login, "LOGIN_SUCCESS", "", ip_address)

            return {"token": token, "user": {"id": user_id, "login": db_login, "full_name": full_name, "role": role, "org": org}}

    except Exception as exc:
        logger.error(f"Auth error: {exc}")
        return None


def register_user(login: str, password: str, full_name: str, role: str = "viewer", email: str = "", org: str = "") -> dict[str, Any] | None:
    try:
        engine = _get_engine()
        pw_hash = hash_password(password)
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    "INSERT INTO users (login, password_hash, full_name, email, role, organization) "
                    "VALUES (:login, :hash, :name, :email, :role, :org) RETURNING id"
                ),
                {"login": login, "hash": pw_hash, "name": full_name, "email": email, "role": role, "org": org},
            )
            user_id = result.scalar()
            conn.commit()
            _log_audit(user_id, login, "USER_REGISTERED", f"Role: {role}", "")
            return {"id": user_id, "login": login, "full_name": full_name, "role": role}
    except Exception as exc:
        logger.error(f"Registration error: {exc}")
        return None


def list_users() -> list[dict[str, Any]]:
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, login, full_name, email, role, organization, is_active, last_login, created_at FROM users ORDER BY id")
            ).fetchall()
            return [
                {
                    "id": r[0], "login": r[1], "full_name": r[2], "email": r[3],
                    "role": r[4], "organization": r[5], "is_active": r[6],
                    "last_login": str(r[7]) if r[7] else "", "created_at": str(r[8]) if r[8] else "",
                }
                for r in rows
            ]
    except Exception as exc:
        logger.error(f"List users error: {exc}")
        return []


def get_audit_log(limit: int = 100) -> list[dict[str, Any]]:
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT id, user_id, login, action, detail, ip_address, created_at FROM audit_log ORDER BY created_at DESC LIMIT :lim"),
                {"lim": limit},
            ).fetchall()
            return [
                {"id": r[0], "user_id": r[1], "login": r[2], "action": r[3], "detail": r[4], "ip_address": r[5], "created_at": str(r[6])}
                for r in rows
            ]
    except Exception as exc:
        logger.error(f"Audit log error: {exc}")
        return []


def has_admin() -> bool:
    try:
        engine = _get_engine()
        with engine.connect() as conn:
            cnt = conn.execute(text("SELECT COUNT(*) FROM users WHERE role = 'admin'")).scalar()
            return cnt > 0
    except Exception:
        return False
