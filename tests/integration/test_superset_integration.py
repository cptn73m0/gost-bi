"""Integration test: verify Superset fork works with GOST BI."""

import os
import sys

import pytest


requires_superset = pytest.mark.skipif(
    "superset" not in sys.modules,
    reason="Superset not installed — run scripts/setup_superset_fork.py first",
)


class TestSupersetIntegration:
    @requires_superset
    def test_superset_imports(self):
        import superset
        assert superset.__version__

    @requires_superset
    def test_gost_bi_config_loads(self):
        config_path = os.environ.get("SUPERSET_CONFIG_PATH")
        if not config_path:
            pytest.skip("SUPERSET_CONFIG_PATH not set")

        import importlib.util
        spec = importlib.util.spec_from_file_location("gost_bi_config", config_path)
        assert spec is not None
        config = importlib.util.module_from_spec(spec)
        if spec.loader:
            spec.loader.exec_module(config)

        assert config.LANGUAGES["ru"]["name"] == "Русский"
        assert config.DEFAULT_TIMEZONE == "Europe/Moscow"

    @requires_superset
    def test_tantor_dialect_registered(self):
        from superset.db_engine_specs.postgres import TantorEngineSpec
        assert TantorEngineSpec.engine == "postgresql"
        assert TantorEngineSpec.engine_name == "Tantor Special Edition"

    @requires_superset
    def test_gost_bi_sql_verifier_integration(self):
        from gost_bi.core.integration import SupersetSQLInterceptor
        interceptor = SupersetSQLInterceptor()
        interceptor.install()
        assert interceptor._original_execute is not None
        assert interceptor.enabled


class TestTantorConnection:
    @requires_superset
    def test_tantor_sqlalchemy_uri(self):
        from sqlalchemy import create_engine
        from sqlalchemy.exc import OperationalError

        db_url = os.environ.get("DATABASE_URL", "postgresql://gostbi:gostbi@localhost:5432/gostbi")

        try:
            engine = create_engine(db_url, connect_args={"connect_timeout": 3})
            with engine.connect() as conn:
                result = conn.exec_driver_sql("SELECT 1 AS test")
                assert result.scalar() == 1
        except OperationalError as exc:
            if "could not connect" in str(exc).lower() or "timeout" in str(exc).lower():
                pytest.skip(f"Tantor/Postgres not available: {exc}")
            raise
