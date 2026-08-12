# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, "src")

PASS = "[PASS]"
FAIL = "[FAIL]"

print("=== GOST BI — Module Import Verification ===\n")

modules = [
    ("gost_bi", "Core"),
    ("gost_bi.quality.sql_verifier", "SQL Verifier"),
    ("gost_bi.monitoring.health_checks", "Health Checks"),
    ("gost_bi.monitoring.feedback_triage", "Feedback Triage"),
    ("gost_bi.connectors.odata_1c", "1C Connector"),
    ("gost_bi.nlp.sql_generator", "NLP -> SQL"),
    ("gost_bi.gost.templates", "GOST Templates"),
    ("gost_bi.core.app", "FastAPI App"),
    ("gost_bi.core.integration", "Superset Integration"),
]

all_ok = True
for module, name in modules:
    try:
        __import__(module)
        print(f"  {PASS} {name}")
    except ImportError as e:
        print(f"  {FAIL} {name}: {e}")
        all_ok = False

print()

if all_ok:
    from gost_bi.quality.sql_verifier import SQLVerifier
    verifier = SQLVerifier()
    report = verifier.verify("SELECT id, name FROM users WHERE active = true")
    print(f"SQL Verifier test: {PASS if report.overall_passed else FAIL}")

    from gost_bi.gost.templates import BUILTIN_TEMPLATES
    print(f"GOST Templates loaded: {len(BUILTIN_TEMPLATES)}")

    from gost_bi.connectors.odata_1c import OData1CConfig
    cfg = OData1CConfig(base_url="http://localhost/demo")
    print(f"1C OData URL: {cfg.service_url}")

print(f"\nResult: {PASS if all_ok else FAIL} all modules")
sys.exit(0 if all_ok else 1)
