"""
Visual Regression Testing — Level 5 of the self-checking system.

Compares screenshots of dashboards and UI components against baselines.
Uses Playwright + OpenCV for pixel-level comparison.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger("gost_bi.quality.visual_regression")


class VisualRegressionRunner:
    THRESHOLD = 0.005  # 0.5% pixel difference

    def __init__(self, baseline_dir: Path, current_dir: Path, diff_dir: Path, threshold: float = 0.005):
        self.baseline_dir = Path(baseline_dir)
        self.current_dir = Path(current_dir)
        self.diff_dir = Path(diff_dir)
        self.threshold = threshold

        self.diff_dir.mkdir(parents=True, exist_ok=True)

    def compare_all(self, names: list[str] | None = None) -> dict[str, dict]:
        if names is None:
            baseline_files = list(self.baseline_dir.glob("*.png"))
            names = [f.stem for f in baseline_files]

        results: dict[str, dict] = {}
        for name in names:
            baseline = self.baseline_dir / f"{name}.png"
            current = self.current_dir / f"{name}.png"

            if not baseline.exists():
                logger.warning(f"Baseline missing for '{name}' — auto-approving current as new baseline")
                if current.exists():
                    import shutil
                    shutil.copy(current, baseline)
                    results[name] = {"status": "NEW_BASELINE", "diff_ratio": 0.0}
                continue

            if not current.exists():
                results[name] = {"status": "MISSING", "diff_ratio": 1.0}
                continue

            result = self.compare_images(name, baseline, current)
            results[name] = result

        return results

    def compare_images(self, name: str, baseline: Path, current: Path) -> dict:
        try:
            import cv2
            import numpy as np

            img_baseline = cv2.imread(str(baseline))
            img_current = cv2.imread(str(current))

            if img_baseline is None:
                return {"status": "ERROR", "error": f"Cannot read baseline: {baseline}"}
            if img_current is None:
                return {"status": "ERROR", "error": f"Cannot read current: {current}"}

            if img_baseline.shape != img_current.shape:
                return {
                    "status": "SIZE_MISMATCH",
                    "diff_ratio": 1.0,
                    "baseline_shape": str(img_baseline.shape),
                    "current_shape": str(img_current.shape),
                }

            diff = cv2.absdiff(img_baseline, img_current)
            diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(diff_gray, 30, 255, cv2.THRESH_BINARY)

            diff_pixels = np.sum(thresh > 0)
            total_pixels = thresh.size
            ratio = diff_pixels / total_pixels

            diff_path = self.diff_dir / f"{name}_diff.png"
            cv2.imwrite(str(diff_path), thresh)

            passed = ratio < self.threshold

            return {
                "status": "PASS" if passed else "FAIL",
                "diff_ratio": round(ratio, 6),
                "diff_pixels": int(diff_pixels),
                "total_pixels": int(total_pixels),
                "threshold": self.threshold,
                "diff_image": str(diff_path),
            }

        except ImportError:
            logger.error("OpenCV not installed. Run: pip install opencv-python-headless")
            return {"status": "SKIP", "error": "OpenCV not installed"}


class PlaywrightScreenshotCapture:
    """Captures screenshots using Playwright for visual regression."""

    def __init__(self, base_url: str = "http://localhost:8088"):
        self.base_url = base_url

    async def capture_dashboards(self, output_dir: Path, dashboard_ids: list[str]) -> list[str]:
        from playwright.async_api import async_playwright

        output_dir.mkdir(parents=True, exist_ok=True)
        captured: list[str] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})

            for dash_id in dashboard_ids:
                await page.goto(f"{self.base_url}/superset/dashboard/{dash_id}/")
                await page.wait_for_load_state("networkidle", timeout=30000)
                await page.wait_for_timeout(2000)

                path = output_dir / f"{dash_id}.png"
                await page.screenshot(path=str(path), full_page=False)
                captured.append(str(path))
                logger.info(f"Captured: {path}")

            await browser.close()

        return captured

    async def capture_component(self, output_dir: Path, route: str, name: str) -> str:
        from playwright.async_api import async_playwright

        output_dir.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1280, "height": 800})

            await page.goto(f"{self.base_url}{route}")
            await page.wait_for_load_state("networkidle", timeout=30000)

            path = output_dir / f"{name}.png"
            await page.screenshot(path=str(path), full_page=False)
            logger.info(f"Captured: {path}")

            await browser.close()

        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Visual Regression Testing — Level 5")
    parser.add_argument("--threshold", type=float, default=0.005, help="Pixel difference threshold (default 0.5%%)")
    parser.add_argument("--baseline", type=str, default="tests/visual/baseline", help="Baseline screenshots directory")
    parser.add_argument("--current", type=str, default="tests/visual/current", help="Current screenshots directory")
    parser.add_argument("--diffs", type=str, default="tests/visual/diffs", help="Diff output directory")
    parser.add_argument("--names", nargs="*", help="Specific screenshot names to compare")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    runner = VisualRegressionRunner(
        baseline_dir=Path(args.baseline),
        current_dir=Path(args.current),
        diff_dir=Path(args.diffs),
        threshold=args.threshold,
    )

    results = runner.compare_all(args.names)

    total = len(results)
    passed = sum(1 for r in results.values() if r["status"] == "PASS")
    failed = total - passed

    logger.info(f"Visual regression: {total} screenshots, {passed} passed, {failed} failed")

    if failed > 0:
        for name, result in results.items():
            if result["status"] != "PASS":
                logger.error(
                    f"  ❌ {name}: {result['status']} "
                    f"(diff: {result.get('diff_ratio', 'N/A')})"
                )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
