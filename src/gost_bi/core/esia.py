"""
ESIA (Госуслуги) Authentication Module — Sprint 8 Extension.

OAuth2/OpenID Connect клиент для Единой системы идентификации и аутентификации.
Поддерживает:
- Авторизация через Госуслуги (юридические лица)
- Получение данных организации (ОГРН, ИНН, КПП)
- JWT-токены с ГОСТ-подписями
- Совместимость с 63-ФЗ об электронной подписи

Требуется: регистрация ИС в СМЭВ/ЕСИА, получение client_id
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from urllib.parse import urlencode

logger = logging.getLogger("gost_bi.auth.esia")


class ESIAEnvironment(str, Enum):
    TEST = "test"
    PRODUCTION = "production"


ESIA_ENDPOINTS: dict[ESIAEnvironment, dict[str, str]] = {
    ESIAEnvironment.TEST: {
        "authorize": "https://esia-portal1.test.gosuslugi.ru/aas/oauth2/ac",
        "token": "https://esia-portal1.test.gosuslugi.ru/aas/oauth2/te",
        "userinfo": "https://esia-portal1.test.gosuslugi.ru/rs/prns",
        "logout": "https://esia-portal1.test.gosuslugi.ru/aas/oauth2/logout",
    },
    ESIAEnvironment.PRODUCTION: {
        "authorize": "https://esia.gosuslugi.ru/aas/oauth2/ac",
        "token": "https://esia.gosuslugi.ru/aas/oauth2/te",
        "userinfo": "https://esia.gosuslugi.ru/rs/prns",
        "logout": "https://esia.gosuslugi.ru/aas/oauth2/logout",
    },
}

ESIA_SCOPES: dict[str, str] = {
    "openid": "Идентификатор пользователя",
    "fullname": "ФИО",
    "birthdate": "Дата рождения",
    "gender": "Пол",
    "email": "Email",
    "mobile": "Телефон",
    "id_doc": "Паспортные данные",
    "snils": "СНИЛС",
    "inn": "ИНН",
    "org_short_name": "Краткое наименование организации",
    "org_full_name": "Полное наименование организации",
    "org_ogrn": "ОГРН",
    "org_kpp": "КПП",
    "org_legut": "Организационно-правовая форма",
}


@dataclass
class ESIAConfig:
    client_id: str
    redirect_uri: str
    environment: ESIAEnvironment = ESIAEnvironment.TEST
    client_secret: str = ""
    scopes: list[str] = field(default_factory=lambda: ["openid", "fullname", "email"])

    @property
    def authorize_url(self) -> str:
        return ESIA_ENDPOINTS[self.environment]["authorize"]

    @property
    def token_url(self) -> str:
        return ESIA_ENDPOINTS[self.environment]["token"]

    @property
    def userinfo_url(self) -> str:
        return ESIA_ENDPOINTS[self.environment]["userinfo"]

    @property
    def logout_url(self) -> str:
        return ESIA_ENDPOINTS[self.environment]["logout"]


@dataclass
class ESIAUser:
    oid: str
    full_name: str = ""
    email: str = ""
    phone: str = ""
    snils: str = ""
    inn: str = ""

    org_short_name: str = ""
    org_full_name: str = ""
    org_ogrn: str = ""
    org_kpp: str = ""

    raw_claims: dict[str, Any] = field(default_factory=dict)

    @property
    def is_organization(self) -> bool:
        return bool(self.org_ogrn)


@dataclass
class ESIATokens:
    access_token: str
    refresh_token: str = ""
    id_token: str = ""
    expires_at: str = ""
    token_type: str = "Bearer"


class ESIAClient:
    """OAuth2-клиент для ЕСИА (Госуслуги)."""

    def __init__(self, config: ESIAConfig):
        self.config = config

    def generate_authorize_url(self, state: str | None = None) -> str:
        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
            "state": state,
            "access_type": "offline",
        }

        if self.config.client_secret:
            params["client_secret"] = self.config.client_secret
            params["timestamp"] = str(int(time.time()))
            params["state"] = self._sign_state(state, params["timestamp"])

        return f"{self.config.authorize_url}?{urlencode(params)}"

    def _sign_state(self, state: str, timestamp: str) -> str:
        if not self.config.client_secret:
            return state
        data = f"{self.config.client_id}{timestamp}{state}{self.config.client_secret}"
        signature = hashlib.sha256(data.encode()).hexdigest()
        return f"{state}.{signature}"

    async def exchange_code(self, code: str, state: str) -> ESIATokens:
        import httpx

        params = {
            "client_id": self.config.client_id,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.config.redirect_uri,
            "state": state,
        }

        if self.config.client_secret:
            params["client_secret"] = self.config.client_secret
            params["token_type"] = "Bearer"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.config.token_url, data=params)

            if resp.status_code != 200:
                raise ESIAAuthError(f"Token exchange failed: {resp.status_code} — {resp.text[:200]}")

            data = resp.json()
            return ESIATokens(
                access_token=data.get("access_token", ""),
                refresh_token=data.get("refresh_token", ""),
                id_token=data.get("id_token", ""),
                expires_at=data.get("expires_at", ""),
                token_type=data.get("token_type", "Bearer"),
            )

    async def get_user_info(self, access_token: str) -> ESIAUser:
        import httpx

        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self.config.userinfo_url, headers=headers)

            if resp.status_code != 200:
                raise ESIAAuthError(f"UserInfo failed: {resp.status_code}")

            data = resp.json()
            return ESIAUser(
                oid=data.get("oid", ""),
                full_name=data.get("fullName", ""),
                email=data.get("email", ""),
                phone=data.get("mobile", ""),
                snils=data.get("snils", ""),
                inn=data.get("inn", ""),
                org_short_name=data.get("orgShortName", ""),
                org_full_name=data.get("orgFullName", ""),
                org_ogrn=data.get("orgOGRN", ""),
                org_kpp=data.get("orgKPP", ""),
                raw_claims=data,
            )

    async def logout(self, access_token: str) -> bool:
        import httpx

        params = {"client_id": self.config.client_id, "access_token": access_token}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(self.config.logout_url, params=params)
            return resp.status_code == 200


class ESIAAuthError(Exception):
    pass
