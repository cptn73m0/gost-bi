"""
1C:Enterprise OData Connector — Sprint 4.

OData REST-клиент для чтения и записи данных 1С:Предприятие.
Поддерживает:
- Справочники (Catalog)
- Документы (Document)
- Регистры сведений (InformationRegister)
- Регистры накопления (AccumulationRegister)
- Планы видов характеристик (ChartOfCharacteristicTypes)

Совместимость: платформа 1С 8.3.18+ с опубликованным OData-интерфейсом.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from urllib.parse import quote

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger("gost_bi.connectors.odata_1c")


class OData1CError(Exception):
    """Base exception for 1C OData errors."""


class OData1CConnectionError(OData1CError):
    """Cannot connect to 1C OData service."""


class OData1CAuthError(OData1CError):
    """Authentication failed."""


class OData1CNotFoundError(OData1CError):
    """Entity or record not found."""


class OData1CValidationError(OData1CError):
    """Data validation error from 1C."""


@dataclass
class OData1CConfig:
    base_url: str
    username: str = ""
    password: str = ""
    timeout: float = 30.0
    max_retries: int = 3
    verify_ssl: bool = True

    @property
    def service_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/odata/standard.odata"

    @property
    def metadata_url(self) -> str:
        return f"{self.service_url}/$metadata"


@dataclass
class OData1CEntity:
    """Represents a 1C OData entity type."""

    name: str
    collection: str
    kind: str = "Catalog"
    fields: list[dict[str, str]] = field(default_factory=list)

    @property
    def full_collection(self) -> str:
        return f"{self.kind}_{self.name}"


@dataclass
class ODataQueryResult:
    raw_data: list[dict[str, Any]]
    next_skip_token: str | None = None
    total_count: int | None = None


class OData1CClient:
    """Async HTTP client for 1C OData interface."""

    def __init__(self, config: OData1CConfig):
        self.config = config
        self._metadata: dict[str, OData1CEntity] | None = None
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args: Any):
        await self.disconnect()

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout),
            verify=self.config.verify_ssl,
            auth=(self.config.username, self.config.password) if self.config.username else None,
        )
        try:
            await self._load_metadata()
        except Exception:
            await self._client.aclose()
            raise

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _load_metadata(self) -> None:
        assert self._client
        resp = await self._client.get(self.config.metadata_url)
        if resp.status_code != 200:
            raise OData1CConnectionError(
                f"Metadata request failed: {resp.status_code} — {resp.text[:200]}"
            )
        self._metadata = self._parse_metadata(resp.text)

    def _parse_metadata(self, xml_text: str) -> dict[str, OData1CEntity]:
        entities: dict[str, OData1CEntity] = {}
        try:
            import xml.etree.ElementTree as ET

            ns = {
                "edmx": "http://schemas.microsoft.com/ado/2007/06/edmx",
                "edm": "http://schemas.microsoft.com/ado/2009/11/edm",
            }
            root = ET.fromstring(xml_text)

            for entity_type in root.iter("{%s}EntityType" % ns["edm"]):
                name = entity_type.get("Name", "")
                entities[name] = OData1CEntity(
                    name=name,
                    collection=name,
                    kind=self._detect_kind(name),
                    fields=[
                        {"name": prop.get("Name", ""), "type": prop.get("Type", "")}
                        for prop in entity_type.findall("edm:Property", ns)
                    ],
                )
        except Exception:
            logger.warning("Could not parse OData metadata XML — entities will be discovered at runtime")
        return entities

    @staticmethod
    def _detect_kind(name: str) -> str:
        if "Справочник" in name or name.startswith("Catalog_"):
            return "Catalog"
        if "Документ" in name or name.startswith("Document_"):
            return "Document"
        if "РегистрСведений" in name or name.startswith("InformationRegister_"):
            return "InformationRegister"
        if "РегистрНакопления" in name or name.startswith("AccumulationRegister_"):
            return "AccumulationRegister"
        if "ПланВидовХарактеристик" in name:
            return "ChartOfCharacteristicTypes"
        return "Catalog"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((OData1CConnectionError, httpx.TimeoutException)),
    )
    async def _request(self, url: str) -> httpx.Response:
        assert self._client
        resp = await self._client.get(url)
        if resp.status_code in (401, 403):
            raise OData1CAuthError(f"Auth failed: {resp.status_code}")
        if resp.status_code == 404:
            raise OData1CNotFoundError(f"Not found: {url}")
        if resp.status_code >= 500:
            raise OData1CConnectionError(f"Server error: {resp.status_code}")
        return resp

    async def query(
        self,
        entity_name: str,
        select: list[str] | None = None,
        filter_expr: str | None = None,
        order_by: str | None = None,
        top: int | None = None,
        skip: int = 0,
        expand: list[str] | None = None,
    ) -> ODataQueryResult:
        assert self._client

        url = f"{self.config.service_url}/{entity_name}"
        params: list[str] = []

        if select:
            params.append(f"$select={','.join(select)}")
        if filter_expr:
            params.append(f"$filter={quote(filter_expr, safe='')}")
        if order_by:
            params.append(f"$orderby={order_by}")
        if top:
            params.append(f"$top={top}")
        if skip:
            params.append(f"$skip={skip}")
        if expand:
            params.append(f"$expand={','.join(expand)}")

        if params:
            url += "?" + "&".join(params)

        logger.debug(f"OData query: {url}")

        resp = await self._request(url)
        data = resp.json()

        records = data.get("value", [])

        result = ODataQueryResult(
            raw_data=records,
            next_skip_token=data.get("odata.nextLink"),
            total_count=data.get("odata.count"),
        )

        logger.info(f"OData query returned {len(records)} records from {entity_name}")
        return result

    async def get_readable_entities(self) -> list[str]:
        if self._metadata:
            return sorted(self._metadata.keys())
        return []

    async def get_entity_fields(self, entity_name: str) -> list[dict[str, str]]:
        if self._metadata and entity_name in self._metadata:
            return self._metadata[entity_name].fields

        try:
            result = await self.query(entity_name, top=1)
            if result.raw_data:
                return [{"name": k, "type": type(v).__name__} for k, v in result.raw_data[0].items()]
        except Exception:
            pass

        return []

    async def health_check(self) -> dict[str, Any]:
        start_time = datetime.now(timezone.utc)
        issues: list[str] = []
        entities_count = 0

        try:
            resp = await self._client.get(self.config.metadata_url) if self._client else None
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            if not resp or resp.status_code != 200:
                issues.append(f"Metadata not accessible (HTTP {resp.status_code if resp else 'N/A'})")
            else:
                entities_count = len(self._metadata or {})

            if latency_ms > 5000:
                issues.append(f"High latency: {latency_ms:.0f}ms")
        except Exception as exc:
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            issues.append(f"Connection failed: {exc}")

        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "latency_ms": round(latency_ms, 0),
            "entities_count": entities_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class OneCReference:
    """Reference (ссылка) to a 1C object — Ref_Key + DataVersion."""

    def __init__(self, ref_key: str, data_version: str = "", presentation: str = ""):
        self.ref_key = ref_key
        self.data_version = data_version
        self.presentation = presentation

    @classmethod
    def from_odata(cls, data: dict[str, Any]) -> OneCReference:
        return cls(
            ref_key=data.get("Ref_Key", ""),
            data_version=data.get("DataVersion", ""),
            presentation=data.get("Description", data.get("DeletionMark", "")),
        )

    def __repr__(self) -> str:
        return f"<1C Ref: {self.presentation or self.ref_key}>"


class OneCDocument:
    """Base class for 1C documents."""

    def __init__(self, entity_name: str, data: dict[str, Any]):
        self.entity_name = entity_name
        self.ref_key = data.get("Ref_Key", "")
        self.number = data.get("Number", "")
        self.date = data.get("Date", "")
        self.posted = data.get("Posted", False)
        self.data_version = data.get("DataVersion", "")
        self.raw = data
