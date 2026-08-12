# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

block_cipher = None

fastapi_imports = collect_submodules("fastapi")
starlette_imports = collect_submodules("starlette")
sqlglot_imports = collect_submodules("sqlglot")
uvicorn_imports = collect_submodules("uvicorn")
sqlalchemy_imports = collect_submodules("sqlalchemy")
psycopg2_binaries = collect_dynamic_libs("psycopg2")

a = Analysis(
    ["scripts/launcher.py"],
    pathex=[],
    binaries=psycopg2_binaries,
    datas=[("src", "src")],
    hiddenimports=(
        fastapi_imports + starlette_imports + sqlglot_imports +
        uvicorn_imports + sqlalchemy_imports +
        ["gost_bi", "gost_bi.core", "gost_bi.core.app",
         "gost_bi.quality", "gost_bi.quality.sql_verifier",
         "gost_bi.monitoring", "gost_bi.monitoring.health_checks",
         "gost_bi.monitoring.feedback_triage",
         "gost_bi.connectors", "gost_bi.connectors.odata_1c",
         "gost_bi.gost", "gost_bi.gost.templates",
         "gost_bi.nlp", "gost_bi.nlp.pipeline_v2_1",
         "gost_bi.core.auth", "gost_bi.core.integration",
         "gost_bi.core.websocket",
         "sqlalchemy", "sqlalchemy.dialects", "sqlalchemy.dialects.postgresql",
         "psycopg2", "httpx", "redis", "redis.asyncio",
         "tenacity", "pydantic", "yaml"]
    ),
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
    win_no_prefer_redirects=False, win_private_assemblies=False,
    cipher=block_cipher, noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name="GOST-BI", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, console=True, target_arch=None,
)
