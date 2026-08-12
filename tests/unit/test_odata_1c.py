"""Unit tests for 1C OData connector — Sprint 4."""

import json

import pytest
from gost_bi.connectors.odata_1c import (
    OData1CClient,
    OData1CConfig,
    OData1CEntity,
    OData1CError,
    ODataQueryResult,
    OneCDocument,
    OneCReference,
)


class TestOData1CConfig:
    def test_service_url_strips_slash(self):
        config = OData1CConfig(base_url="http://1c-server/mybase/")
        assert config.service_url == "http://1c-server/mybase/odata/standard.odata"

    def test_service_url_no_slash(self):
        config = OData1CConfig(base_url="http://1c-server/mybase")
        assert config.service_url == "http://1c-server/mybase/odata/standard.odata"

    def test_metadata_url(self):
        config = OData1CConfig(base_url="http://1c-server")
        assert config.metadata_url == "http://1c-server/odata/standard.odata/$metadata"

    def test_default_values(self):
        config = OData1CConfig(base_url="http://localhost")
        assert config.timeout == 30.0
        assert config.max_retries == 3
        assert config.verify_ssl is True


class TestOData1CEntity:
    def test_full_collection(self):
        entity = OData1CEntity(name="Catalog_Номенклатура", collection="Catalog_Номенклатура", kind="Catalog")
        assert entity.full_collection == "Catalog_Catalog_Номенклатура"

    def test_fields(self):
        entity = OData1CEntity(
            name="Catalog_Товары",
            collection="Catalog_Товары",
            kind="Catalog",
            fields=[{"name": "Ref_Key", "type": "Edm.Guid"}],
        )
        assert len(entity.fields) == 1


class TestODataQueryResult:
    def test_empty_result(self):
        result = ODataQueryResult(raw_data=[])
        assert len(result.raw_data) == 0
        assert result.next_skip_token is None
        assert result.total_count is None

    def test_with_data(self):
        result = ODataQueryResult(raw_data=[{"id": 1}], total_count=42, next_skip_token="?$skip=100")
        assert result.total_count == 42
        assert result.next_skip_token == "?$skip=100"


class TestOneCReference:
    def test_from_odata(self):
        ref = OneCReference.from_odata({"Ref_Key": "guid-123", "DataVersion": "v1"})
        assert ref.ref_key == "guid-123"
        assert ref.data_version == "v1"

    def test_repr(self):
        ref = OneCReference(ref_key="guid-abc", presentation="Товар #42")
        assert "Товар #42" in repr(ref)


class TestOneCDocument:
    def test_from_data(self):
        doc = OneCDocument(
            "Document_РеализацияТоваров",
            {"Ref_Key": "doc-1", "Number": "РТ-00001", "Date": "2026-01-15", "Posted": True},
        )
        assert doc.ref_key == "doc-1"
        assert doc.number == "РТ-00001"
        assert doc.posted is True


class TestOData1CClientConfig:
    def test_client_requires_base_url(self):
        config = OData1CConfig(base_url="http://1c:8080/demo")
        client = OData1CClient(config)
        assert client.config.base_url == "http://1c:8080/demo"

    def test_kind_detection(self):
        assert OData1CClient._detect_kind("Catalog_Номенклатура") == "Catalog"
        assert OData1CClient._detect_kind("Document_ПоступлениеТоваровУслуг") == "Document"
        assert OData1CClient._detect_kind("InformationRegister_ЦеныНоменклатуры") == "InformationRegister"
        assert OData1CClient._detect_kind("AccumulationRegister_ОстаткиТоваров") == "AccumulationRegister"
        assert OData1CClient._detect_kind("ChartOfCharacteristicTypes_СвойстваОбъектов") == "ChartOfCharacteristicTypes"
        assert OData1CClient._detect_kind("Unknown_Thing") == "Catalog"


class TestOData1CErrors:
    def test_connection_error(self):
        err = OData1CError("connection lost")
        assert str(err) == "connection lost"

    def test_auth_error(self):
        from gost_bi.connectors.odata_1c import OData1CAuthError
        err = OData1CAuthError("bad credentials")
        assert isinstance(err, OData1CError)

    def test_not_found_error(self):
        from gost_bi.connectors.odata_1c import OData1CNotFoundError
        err = OData1CNotFoundError("entity missing")
        assert isinstance(err, OData1CError)
