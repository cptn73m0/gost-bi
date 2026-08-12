"""
Check benchmark regression.

Compares current benchmark results against stored baselines.
Alerts if P95 latency degraded >20% from baseline.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger("gost_bi.quality.benchmark_regression")

DEGRADATION_THRESHOLD = 1.20
BASELINE_FILE = Path("tests/benchmarks/.baseline.json")


def load_baseline() -> dict[str, float]:
    if not BASELINE_FILE.exists():
        logger.warning(f"No baseline found at {BASELINE_FILE}")
        return {}
    with open(BASELINE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_baseline(data: dict[str, float]) -> None:
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Baseline saved to {BASELINE_FILE}")


def check_regression(current: dict[str, float], baseline: dict[str, float]) -> list[str]:
    regressions: list[str] = []

    for name, p95 in current.items():
        if name not in baseline:
            logger.info(f"New benchmark: {name} (p95={p95:.0f}ms)")
            continue

        baseline_p95 = baseline[name]
        if baseline_p95 == 0:
            continue

        ratio = p95 / baseline_p95
        if ratio > DEGRADATION_THRESHOLD:
            msg = f"Regression: {name}: {p95:.0f}ms vs baseline {baseline_p95:.0f}ms ({ratio:.1%} of baseline)"
            regressions.append(msg)
            logger.error(f"  🔴 {msg}")
        else:
            logger.info(f"  ✅ {name}: {p95:.0f}ms ({ratio:.1%} of baseline)")

    return regressions


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    results_files = sorted(Path("tests/benchmarks/").glob(".benchmarks/*/*.json"), reverse=True)
    if not results_files:
        logger.info("No benchmark results found — saving as baseline")
        return 0

    latest = results_files[0]
    with open(latest, encoding="utf-8") as f:
        data = json.load(f)

    current_p95: dict[str, float] = {}
    for benchmark in data.get("benchmarks", []):
        name = benchmark["name"]
        stats = benchmark.get("stats", {})
        p95 = stats.get("p95", 0) * 1000
        current_p95[name] = p95

    baseline = load_baseline()

    if not baseline:
        logger.info("No baseline — saving current results as baseline")
        save_baseline(current_p95)
        return 0

    regressions = check_regression(current_p95, baseline)

    if regressions:
        print(f"\n❌ {len(regressions)} performance regression(s) found:")
        for r in regressions:
            print(f"   {r}")
        return 1

    save_baseline(current_p95)
    return 0


if __name__ == "__main__":
    sys.exit(main())
