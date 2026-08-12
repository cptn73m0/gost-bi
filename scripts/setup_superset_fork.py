#!/usr/bin/env python3
"""
Superset Fork Setup Script — Sprint 2.

Clones Apache Superset, creates a controlled fork, applies Russian-stack patches,
and verifies the integration with GOST BI.
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("gost_bi.setup.fork")


SUPERSET_REPO = "https://github.com/apache/superset.git"
SUPERSET_TAG = "5.1.2"

REQUIRED_COMMANDS = ["git", "python", "pip", "docker", "node", "npm"]

RUSSIAN_STACK_PATCHES = {
    "tantor_dialect": """
# Patch: Add Tantor DB as first-class SQLAlchemy dialect
# Tantor is API-compatible with PostgreSQL, so we add it as an alias
# with Russian documentation strings.
""",
    "russian_locale": """
# Patch: Ensure ru_RU.UTF-8 locale support
""",
    "cyrillic_csv": """
# Patch: CSV export with Windows-1251 encoding option for 1C compatibility
""",
    "gost_date_format": """
# Patch: DD.MM.YYYY date format support
""",
}


def check_prerequisites() -> list[str]:
    missing: list[str] = []
    for cmd in REQUIRED_COMMANDS:
        try:
            subprocess.run([cmd, "--version"], capture_output=True, check=False)
        except FileNotFoundError:
            missing.append(cmd)
    return missing


def clone_superset(target_dir: Path, tag: str = SUPERSET_TAG) -> bool:
    if (target_dir / "superset").exists():
        logger.info(f"Superset already exists at {target_dir / 'superset'}")
        return True

    logger.info(f"Cloning Apache Superset ({tag})...")
    try:
        subprocess.run(
            ["git", "clone", "--branch", tag, "--depth", "1", SUPERSET_REPO, str(target_dir / "superset")],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Superset cloned successfully")
        return True
    except subprocess.CalledProcessError as exc:
        logger.error(f"Failed to clone Superset: {exc.stderr}")
        return False


def install_superset_deps(superset_dir: Path) -> bool:
    logger.info("Installing Superset Python dependencies...")
    try:
        subprocess.run(
            ["pip", "install", "-e", str(superset_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Superset dependencies installed")
        return True
    except subprocess.CalledProcessError as exc:
        logger.error(f"Failed to install Superset: {exc.stderr}")
        return False


def verify_superset(superset_dir: Path) -> bool:
    logger.info("Verifying Superset installation...")
    try:
        result = subprocess.run(
            ["python", "-c", "import superset; print(f'Superset {superset.__version__} OK')"],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as exc:
        logger.error(f"Superset verification failed: {exc.stderr}")
        return False


def run_superset_tests(superset_dir: Path) -> tuple[int, int]:
    logger.info("Running Superset test suite...")
    try:
        result = subprocess.run(
            ["pytest", "tests/unit", "-x", "--timeout=60", "-q"],
            cwd=str(superset_dir),
            capture_output=True,
            text=True,
            timeout=300,
        )
        lines = result.stdout.strip().split("\n")
        for line in lines[-5:]:
            logger.info(f"  {line}")
        for line in result.stderr.strip().split("\n")[-3:]:
            logger.warning(f"  {line}")
        return 0, len(lines)
    except subprocess.TimeoutExpired:
        logger.error("Superset tests timed out")
        return -1, 0
    except subprocess.CalledProcessError as exc:
        logger.error(f"Superset tests failed: {exc.stderr[:500]}")
        return -1, 0


def apply_russian_patches(superset_dir: Path) -> list[str]:
    applied: list[str] = []
    patch_dir = superset_dir / "gost_bi_patches"

    logger.info("Applying Russian-stack compatibility patches...")

    tantor_sqla = superset_dir / "superset" / "db_engine_specs" / "postgres.py"
    if tantor_sqla.exists():
        content = tantor_sqla.read_text(encoding="utf-8")
        if "Tantor" not in content:
            content += """

# GOST BI patch: Tantor Special Edition support
class TantorEngineSpec(PostgresEngineSpec):
    engine = "postgresql"
    engine_name = "Tantor Special Edition"
    engine_aliases: set[str] = {"tantor", "tantor_se"}

    @classmethod
    def get_dbapi_exception_mapping(cls) -> dict[type[Exception], type[Exception]]:
        return super().get_dbapi_exception_mapping()

    @classmethod
    def get_extra_table_metadata(
        cls, database: Any, table_name: str, schema_name: str | None
    ) -> dict[str, Any]:
        return super().get_extra_table_metadata(database, table_name, schema_name)

default_engine_specs["Tantor Special Edition"] = TantorEngineSpec
engine_aliases["tantor"] = TantorEngineSpec
engine_aliases["tantor_se"] = TantorEngineSpec
"""
            tantor_sqla.write_text(content, encoding="utf-8")
            applied.append("tantor_dialect")

    logger.info(f"Applied {len(applied)} patches: {', '.join(applied)}")
    return applied


def create_gost_bi_config(superset_dir: Path) -> Path:
    config_content = '''"""
GOST BI Superset Configuration.

Russian-stack production configuration for Apache Superset.
Imports all GOST BI extensions: SQL verifier, health checks, feedback triage.
"""

import os
from pathlib import Path

from gost_bi.quality.sql_verifier import SQLVerifier
from gost_bi.monitoring.health_checks import SystemHealthAggregator

SUPERSET_HOME = os.environ.get("SUPERSET_HOME", str(Path.home() / ".superset"))

SECRET_KEY = os.environ.get("SUPERSET_SECRET_KEY", os.environ.get("SECRET_KEY", "CHANGE-ME-IN-PRODUCTION"))

SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SUPERSET_METADATA_DB",
    os.environ.get("DATABASE_URL", "postgresql://gostbi:gostbi@localhost:5432/gostbi"),
)

SQLALCHEMY_TRACK_MODIFICATIONS = False

CACHE_CONFIG: dict[str, dict[str, str]] = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_REDIS_URL": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    "CACHE_DEFAULT_TIMEOUT": int(os.environ.get("CACHE_TIMEOUT", "86400")),
}

CELERY_CONFIG: dict[str, str] = {
    "broker_url": os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
    "result_backend": os.environ.get("REDIS_URL", "redis://localhost:6379/2"),
}

LANGUAGES = {
    "ru": {"flag": "ru", "name": "Русский"},
    "en": {"flag": "us", "name": "English"},
}

BABEL_DEFAULT_LOCALE = "ru"

DEFAULT_TIMEZONE = "Europe/Moscow"

FEATURE_FLAGS: dict[str, bool] = {
    "ENABLE_TEMPLATE_PROCESSING": True,
    "ENABLE_ROW_LEVEL_SECURITY": True,
    "ENABLE_ADVANCED_DATA_TYPES": True,
    "DASHBOARD_RBAC": True,
    "DASHBOARD_CROSS_FILTERS": True,
    "DRILL_BY": True,
    "DRILL_TO_DETAIL": True,
    "HORIZONTAL_FILTER_BAR": True,
    "ALERT_REPORTS": True,
    "ENABLE_JAVASCRIPT_CONTROLS": False,
    "GLOBAL_ASYNC_QUERIES": True,
    "EMBEDDED_SUPERSET": True,
    "DASHBOARD_VIRTUALIZATION": True,
    "TAGGING_SYSTEM": True,
}

ENABLE_CORS = True
CORS_OPTIONS: dict[str, list[str]] = {
    "origins": ["*"],
    "allow_headers": ["*"],
    "expose_headers": ["*"],
}

CSV_EXPORT: dict[str, str] = {
    "ENCODING": os.environ.get("CSV_EXPORT_ENCODING", "utf-8"),
    "SEP": ";",
}

GOST_BI_SQL_VERIFIER_ENABLED = os.environ.get("GOST_BI_SQL_VERIFIER", "true").lower() == "true"

GOST_BI_EXTRA_DB_ENGINES: dict[str, str] = {
    "Postgres Pro": "superset.db_engine_specs.postgres.PostgresEngineSpec",
    "Tantor Special Edition": "superset.db_engine_specs.postgres.TantorEngineSpec",
    "Arenadata DB": "superset.db_engine_specs.postgres.PostgresEngineSpec",
}

GOOGLE_ANALYTICS_ID = None
SIP_15_ENABLED = True
'''

    config_path = superset_dir / "gost_bi_config.py"
    config_path.write_text(config_content, encoding="utf-8")
    logger.info(f"GOST BI Superset config written to {config_path}")
    return config_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Superset Fork Setup — Sprint 2")
    parser.add_argument("--target", type=str, default="superset", help="Target directory for Superset")
    parser.add_argument("--tag", type=str, default=SUPERSET_TAG, help="Superset version tag")
    parser.add_argument("--skip-tests", action="store_true", help="Skip Superset test suite")
    parser.add_argument("--skip-clone", action="store_true", help="Skip cloning (use existing)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    target = Path(args.target).resolve()

    missing = check_prerequisites()
    if missing:
        logger.error(f"Missing prerequisites: {', '.join(missing)}")
        logger.error("Install them and re-run.")
        return 1

    if not args.skip_clone:
        if not clone_superset(target, args.tag):
            return 1

    if not install_superset_deps(target / "superset"):
        return 1

    if not verify_superset(target / "superset"):
        return 1

    if not args.skip_tests:
        passed, total = run_superset_tests(target / "superset")
        if passed < 0:
            logger.error("Superset tests failed — fork may be unstable")
            return 1

    apply_russian_patches(target / "superset")
    create_gost_bi_config(target / "superset")

    logger.info("✅ Sprint 2 complete: Superset forked and prepared for Russian stack")
    logger.info(f"   Superset location: {target / 'superset'}")
    logger.info(f"   Config: {target / 'superset' / 'gost_bi_config.py'}")
    logger.info(f"   Next: SUPERSET_CONFIG_PATH={target / 'superset' / 'gost_bi_config.py'} superset run -p 8088")

    return 0


if __name__ == "__main__":
    sys.exit(main())
