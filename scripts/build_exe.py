#!/usr/bin/env python3
"""
Build GOST BI EXE for Windows.

Requirements: pip install pyinstaller
Output: dist/GOST-BI.exe (~15-25 MB, self-contained, no Python needed)

Usage:
    python build_exe.py              # Build EXE
    python build_exe.py --clean      # Clean + build
    python build_exe.py --run        # Build + run
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = PROJECT_ROOT / "build" / "gost-bi.spec"
DIST_DIR = PROJECT_ROOT / "dist"


def clean() -> None:
    for d in ["build", "dist", "__pycache__"]:
        path = PROJECT_ROOT / d
        if path.exists():
            for item in path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            print(f"  Cleaned: {d}")
    for spec in PROJECT_ROOT.glob("*.spec"):
        if spec != SPEC_FILE:
            spec.unlink()
            print(f"  Cleaned: {spec.name}")


def check_prerequisites() -> bool:
    try:
        subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("PyInstaller not installed. Run: pip install pyinstaller")
        return False


def build_frontend() -> bool:
    frontend_dir = PROJECT_ROOT / "frontend"
    if not (frontend_dir / "package.json").exists():
        return True

    dist = frontend_dir / "dist"
    if dist.exists() and list(dist.glob("*.html")):
        print("  Frontend already built — skipping")
        return True

    print("  npm not available — skipping frontend build (API-only mode)")
    return True


def build_exe() -> bool:
    print(f"Building GOST-BI.exe...")
    print(f"  Spec: {SPEC_FILE}")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC_FILE),
        "--clean",
        "--noconfirm",
        "--distpath", str(DIST_DIR),
    ]

    try:
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)
        exe_path = DIST_DIR / "GOST-BI.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\n  GOST-BI.exe built successfully: {exe_path}")
            print(f"  Size: {size_mb:.1f} MB")
            return True
        else:
            print("  EXE not found after build")
            return False
    except subprocess.CalledProcessError as e:
        print(f"  Build failed: {e}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Build GOST BI EXE")
    parser.add_argument("--clean", action="store_true", help="Clean before build")
    parser.add_argument("--run", action="store_true", help="Run EXE after build")
    args = parser.parse_args()

    if args.clean:
        clean()

    if not check_prerequisites():
        return 1

    if not build_frontend():
        print("Warning: continuing without frontend")

    if not build_exe():
        return 1

    if args.run:
        exe = DIST_DIR / "GOST-BI.exe"
        if exe.exists():
            subprocess.run([str(exe)])

    return 0


if __name__ == "__main__":
    sys.exit(main())
