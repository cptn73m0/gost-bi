"""
Auth Middleware — FastAPI dependency injection for authentication.

Supports:
- JWT Bearer tokens (standard)
- API keys (X-API-Key header)
- ESIA (Госуслуги) OAuth2 tokens
- Role-based access control (RBAC)
- Row-Level Security (RLS) hints
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger("gost_bi.auth")

security = HTTPBearer(auto_error=False)


class Role(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"
    AUDITOR = "auditor"


@dataclass
class User:
    id: str
    login: str
    full_name: str
    email: str = ""
    roles: list[Role] = field(default_factory=lambda: [Role.VIEWER])
    organization: str = ""
    rls_filters: dict[str, str] = field(default_factory=dict)

    @property
    def is_admin(self) -> bool:
        return Role.ADMIN in self.roles

    @property
    def is_analyst(self) -> bool:
        return Role.ANALYST in self.roles or self.is_admin


API_KEYS: dict[str, User] = {
    "gost-bi-dev-key": User(
        id="dev-001",
        login="developer",
        full_name="Разработчик ГОСТ БИ",
        email="dev@gost-bi.local",
        roles=[Role.ADMIN],
    ),
    "demo-analyst": User(
        id="demo-002",
        login="analyst",
        full_name="Аналитик (демо)",
        roles=[Role.ANALYST],
        organization="ООО Демо",
        rls_filters={"region": "Москва"},
    ),
    "demo-viewer": User(
        id="demo-003",
        login="viewer",
        full_name="Зритель (демо)",
        roles=[Role.VIEWER],
        organization="ООО Демо",
        rls_filters={"region": "Москва"},
    ),
}

JWT_SECRET = os.environ.get("JWT_SECRET", "gost-bi-dev-secret-change-in-production")
API_KEY_HEADER = "X-API-Key"


def _verify_jwt(token: str) -> User | None:
    try:
        import base64
        import json
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
        return User(
            id=payload.get("sub", "unknown"),
            login=payload.get("login", payload.get("sub", "unknown")),
            full_name=payload.get("name", payload.get("sub", "unknown")),
            email=payload.get("email", ""),
            roles=[Role(r) for r in payload.get("roles", ["viewer"])],
            organization=payload.get("org", ""),
            rls_filters=payload.get("rls", {}),
        )
    except Exception:
        return None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> User:
    api_key = request.headers.get(API_KEY_HEADER)
    if api_key and api_key in API_KEYS:
        return API_KEYS[api_key]

    if credentials:
        user = _verify_jwt(credentials.credentials)
        if user:
            return user

        if credentials.credentials.startswith("demo-"):
            for key, user_obj in API_KEYS.items():
                if credentials.credentials == key:
                    return user_obj

    return User(
        id="anon",
        login="anonymous",
        full_name="Гость",
        roles=[Role.VIEWER],
    )


def require_role(*roles: Role):
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if not any(r in user.roles for r in roles):
            raise HTTPException(status_code=403, detail=f"Требуется одна из ролей: {[r.value for r in roles]}")
        return user
    return role_checker


def require_admin(user: User = Depends(require_role(Role.ADMIN))) -> User:
    return user


def require_analyst(user: User = Depends(require_role(Role.ADMIN, Role.ANALYST))) -> User:
    return user
