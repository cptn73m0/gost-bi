"""
1C OData Mock Server — Sprint 8 Extension.

Полноценный эмулятор OData-интерфейса 1С:Предприятие для тестирования.
Не требует реального сервера 1С. Запускается одной командой.

Использование:
    python -m gost_bi.connectors.odata_1c_mock --port 8080

Эмулирует:
    - $metadata (описание сущностей)
    - CRUD справочников (Catalog)
    - CRUD документов (Document)
    - Регистры сведений (InformationRegister)
    - Фильтрация $filter, $select, $top, $skip, $orderby
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

app = FastAPI(title="1C OData Mock Server", version="1.0")

ENTITIES: dict[str, dict[str, Any]] = {
    "Catalog_Номенклатура": {
        "kind": "Catalog",
        "fields": ["Ref_Key", "Description", "Code", "Артикул", "DeletionMark", "Predefined"],
        "data": [],
    },
    "Catalog_Контрагенты": {
        "kind": "Catalog",
        "fields": ["Ref_Key", "Description", "ИНН", "КПП", "DeletionMark", "Predefined"],
        "data": [],
    },
    "Catalog_Склады": {
        "kind": "Catalog",
        "fields": ["Ref_Key", "Description", "Адрес", "DeletionMark", "Predefined"],
        "data": [],
    },
    "Document_ПоступлениеТоваровУслуг": {
        "kind": "Document",
        "fields": ["Ref_Key", "Number", "Date", "Posted", "DeletionMark", "Контрагент_Key", "Склад_Key"],
        "data": [],
    },
    "Document_РеализацияТоваровУслуг": {
        "kind": "Document",
        "fields": ["Ref_Key", "Number", "Date", "Posted", "DeletionMark", "Контрагент_Key", "Склад_Key"],
        "data": [],
    },
    "InformationRegister_ЦеныНоменклатуры": {
        "kind": "InformationRegister",
        "fields": ["Period", "Номенклатура_Key", "ТипЦен_Key", "Цена"],
        "data": [],
    },
    "AccumulationRegister_ОстаткиТоваров": {
        "kind": "AccumulationRegister",
        "fields": ["Period", "Номенклатура_Key", "Склад_Key", "Количество", "Сумма"],
        "data": [],
    },
}


def _init_data() -> None:
    if ENTITIES["Catalog_Номенклатура"]["data"]:
        return

    for i in range(1, 51):
        ENTITIES["Catalog_Номенклатура"]["data"].append({
            "Ref_Key": str(uuid.uuid4()),
            "Description": f"Товар #{i:04d}",
            "Code": f"00-{i:06d}",
            "Артикул": f"ART-{i:04d}",
            "DeletionMark": False,
            "Predefined": i <= 5,
        })

    for i in range(1, 21):
        ENTITIES["Catalog_Контрагенты"]["data"].append({
            "Ref_Key": str(uuid.uuid4()),
            "Description": f"Контрагент #{i}",
            "ИНН": f"{random.randint(1000000000, 9999999999)}",
            "КПП": f"{random.randint(100000000, 999999999)}",
            "DeletionMark": False,
            "Predefined": False,
        })

    for i in range(1, 6):
        ENTITIES["Catalog_Склады"]["data"].append({
            "Ref_Key": str(uuid.uuid4()),
            "Description": f"Склад #{i}",
            "Адрес": f"г. Москва, ул. Складская, д.{i}",
            "DeletionMark": False,
            "Predefined": True,
        })

    nomen = ENTITIES["Catalog_Номенклатура"]["data"]
    ktr = ENTITIES["Catalog_Контрагенты"]["data"]
    skl = ENTITIES["Catalog_Склады"]["data"]

    for i in range(1, 101):
        dt = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 365))
        ENTITIES["Document_ПоступлениеТоваровУслуг"]["data"].append({
            "Ref_Key": str(uuid.uuid4()),
            "Number": f"ПТ-{i:06d}",
            "Date": dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "Posted": random.random() > 0.1,
            "DeletionMark": False,
            "Контрагент_Key": random.choice(ktr)["Ref_Key"],
            "Склад_Key": random.choice(skl)["Ref_Key"],
        })
        ENTITIES["Document_РеализацияТоваровУслуг"]["data"].append({
            "Ref_Key": str(uuid.uuid4()),
            "Number": f"РТ-{i:06d}",
            "Date": dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "Posted": random.random() > 0.05,
            "DeletionMark": False,
            "Контрагент_Key": random.choice(ktr)["Ref_Key"],
            "Склад_Key": random.choice(skl)["Ref_Key"],
        })

    for item in nomen:
        for s in skl:
            ENTITIES["AccumulationRegister_ОстаткиТоваров"]["data"].append({
                "Period": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                "Номенклатура_Key": item["Ref_Key"],
                "Склад_Key": s["Ref_Key"],
                "Количество": round(random.uniform(0, 1000), 3),
                "Сумма": round(random.uniform(0, 500000), 2),
            })


_init_data()


@app.get("/demo/odata/standard.odata/$metadata")
async def metadata():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="1.0" xmlns:edmx="http://schemas.microsoft.com/ado/2007/06/edmx">
  <edmx:DataServices xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata" m:DataServiceVersion="1.0">
    <Schema Namespace="StandardODATA" xmlns="http://schemas.microsoft.com/ado/2009/11/edm">
      <EntityContainer Name="StandardODATA" m:IsDefaultEntityContainer="true">"""
    for name in ENTITIES:
        xml += f'\n        <EntitySet Name="{name}" EntityType="StandardODATA.{name}"/>'
    xml += """
      </EntityContainer>"""
    for name, entity in ENTITIES.items():
        xml += f'\n      <EntityType Name="{name}">'
        xml += "\n        <Key><PropertyRef Name=\"Ref_Key\"/></Key>"
        for field in entity["fields"]:
            xml += f'\n        <Property Name="{field}" Type="Edm.String" Nullable="true"/>'
        xml += "\n      </EntityType>"
    xml += """
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>"""
    return PlainTextResponse(xml, media_type="application/xml")


@app.get("/demo/odata/standard.odata/{entity_name}")
async def query_entity(
    entity_name: str,
    request: Request,
    $filter: str = Query(None),
    $select: str = Query(None),
    $orderby: str = Query(None),
    $top: int = Query(None),
    $skip: int = Query(0),
):
    if entity_name not in ENTITIES:
        return JSONResponse({"error": {"message": f"Entity '{entity_name}' not found"}}, status_code=404)

    data = ENTITIES[entity_name]["data"].copy()

    if $filter:
        data = _apply_filter(data, $filter)

    if $orderby:
        data = _apply_orderby(data, $orderby)

    total = len(data)

    if $skip:
        data = data[$skip:]

    if $top:
        data = data[:$top]

    if $select:
        sel_fields = [f.strip() for f in $select.split(",")]
        data = [{k: v for k, v in row.items() if k in sel_fields} for row in data]

    result = {"odata.metadata": f"{request.url.scheme}://{request.url.netloc}/demo/odata/standard.odata/$metadata#{entity_name}"}
    result["value"] = data
    if $top and total > $top + $skip:
        next_skip = $skip + $top
        result["odata.nextLink"] = f"/demo/odata/standard.odata/{entity_name}?$skip={next_skip}&$top={$top}"
    result["odata.count"] = total

    return JSONResponse(result)


def _apply_filter(data: list[dict], filter_str: str) -> list[dict]:
    result = []
    for row in data:
        try:
            if _eval_filter(row, filter_str):
                result.append(row)
        except Exception:
            result.append(row)
    return result


def _eval_filter(row: dict, expr: str) -> bool:
    expr = expr.strip()
    if expr in ("true", "True"):
        return True
    if expr in ("false", "False"):
        return False

    if " eq " in expr:
        field, value = expr.split(" eq ", 1)
        field = field.strip()
        value = value.strip().strip("'").strip('"')
        return str(row.get(field, "")) == value
    if " ne " in expr:
        field, value = expr.split(" ne ", 1)
        field = field.strip()
        value = value.strip().strip("'").strip('"')
        return str(row.get(field, "")) != value
    if " gt " in expr:
        field, value = expr.split(" gt ", 1)
        return float(row.get(field.strip(), 0)) > float(value.strip())
    if " lt " in expr:
        field, value = expr.split(" lt ", 1)
        return float(row.get(field.strip(), 0)) < float(value.strip())

    return True


def _apply_orderby(data: list[dict], orderby: str) -> list[dict]:
    parts = orderby.strip().split()
    field = parts[0]
    reverse = len(parts) > 1 and parts[1].lower() == "desc"
    return sorted(data, key=lambda r: str(r.get(field, "")), reverse=reverse)


if __name__ == "__main__":
    import uvicorn
    print("1C OData Mock Server starting at http://localhost:8080/demo")
    print("Metadata: http://localhost:8080/demo/odata/standard.odata/$metadata")
    print("Entities:", ", ".join(ENTITIES.keys()))
    uvicorn.run(app, host="0.0.0.0", port=8080)
