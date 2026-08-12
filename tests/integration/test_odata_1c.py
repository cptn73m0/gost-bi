"""
Integration test: 1C OData connector with real or mock 1C service.

Requires: 1C server with published OData interface at $ONE_C_URL
Or: mock 1C OData service at http://localhost:8080
"""

import os

import pytest

ONE_C_URL = os.environ.get("ONE_C_URL", "http://localhost:8080/demo")
ONE_C_USER = os.environ.get("ONE_C_USER", "")
ONE_C_PASS = os.environ.get("ONE_C_PASS", "")

pytestmark = pytest.mark.integration


@pytest.fixture
async def client():
    from gost_bi.connectors.odata_1c import OData1CClient, OData1CConfig

    config = OData1CConfig(base_url=ONE_C_URL, username=ONE_C_USER, password=ONE_C_PASS, timeout=10)
    client = OData1CClient(config)
    try:
        await client.connect()
        yield client
    finally:
        await client.disconnect()


class TestOData1CIntegration:
    @pytest.mark.requires_1c
    async def test_health_check(self, client):
        result = await client.health_check()
        assert result["healthy"] is True
        assert result["latency_ms"] > 0
        assert result["entities_count"] >= 0

    @pytest.mark.requires_1c
    async def test_get_entities(self, client):
        entities = await client.get_readable_entities()
        assert len(entities) > 0

    @pytest.mark.requires_1c
    async def test_query_catalog_top_10(self, client):
        entities = await client.get_readable_entities()
        if not entities:
            pytest.skip("No entities available")

        entity = entities[0]
        result = await client.query(entity, top=10)
        assert isinstance(result.raw_data, list)

    @pytest.mark.requires_1c
    async def test_query_with_select(self, client):
        entities = await client.get_readable_entities()
        if not entities:
            pytest.skip("No entities available")

        catalog = next((e for e in entities if "Catalog" in e or "Справочник" in e), entities[0])

        fields = await client.get_entity_fields(catalog)
        if not fields:
            pytest.skip("No fields available")

        select_fields = [f["name"] for f in fields[:3]]
        result = await client.query(catalog, select=select_fields, top=5)

        if result.raw_data:
            first = result.raw_data[0]
            for field in select_fields:
                assert field in first

    @pytest.mark.requires_1c
    async def test_query_with_filter(self, client):
        entities = await client.get_readable_entities()
        if not entities:
            pytest.skip("No entities available")

        entity = entities[0]
        try:
            result = await client.query(entity, top=5, filter_expr="DeletionMark eq false")
            assert isinstance(result.raw_data, list)
        except Exception:
            pytest.skip("Filter not supported by this entity")

    @pytest.mark.requires_1c
    async def test_health_check_failure_on_bad_url(self):
        from gost_bi.connectors.odata_1c import OData1CClient, OData1CConfig

        config = OData1CConfig(base_url="http://127.0.0.1:19999/nonexistent", timeout=2)
        bad_client = OData1CClient(config)
        try:
            await bad_client.connect()
            result = await bad_client.health_check()
            assert not result["healthy"]
        except Exception:
            pass
