import sys
sys.path.insert(0, "src")

from gost_bi import __version__
from gost_bi.quality.sql_verifier import SQLVerifier, SQLVerificationSuite

print(f"GOST BI v{__version__}")
print()

verifier = SQLVerifier()
cases = [
    ("valid simple", "SELECT id, name FROM users WHERE active = true", True),
    ("valid complex", "SELECT region, SUM(revenue) AS total FROM sales WHERE date >= '2026-01-01' GROUP BY region", True),
    ("DROP blocked", "DROP TABLE users", False),
    ("TRUNCATE blocked", "TRUNCATE TABLE orders", False),
    ("DELETE blocked", "DELETE FROM audit_log", False),
    ("injection OR", "SELECT * FROM users WHERE email = '' OR '1'='1'", False),
    ("injection UNION", "SELECT id FROM users WHERE name = '' UNION SELECT password FROM admin_users", False),
    ("semicolon DROP", "SELECT 1; DROP TABLE users", False),
    ("ALTER blocked", "ALTER TABLE users ADD COLUMN phone VARCHAR(20)", False),
    ("syntax error", "SELECT * FORM users", False),
    ("empty", "", False),
]

all_pass = True
for name, sql, expect_pass in cases:
    report = verifier.verify(sql)
    ok = report.overall_passed == expect_pass
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  [{status}] {name}: {sql[:70]}")

print()

suite = SQLVerificationSuite()
passed, total = suite.run_suite()
print(f"SQL Suite: {passed}/{total}")

print()
print(f"Result: {'PASS' if all_pass and passed == total else 'FAIL'}")
print("GOST BI Sprint 8 — Pilot launch complete")
