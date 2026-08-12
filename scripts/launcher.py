#!/usr/bin/env python3
"""
GOST BI Launcher v2 — Starts server in-process (reliable for PyInstaller).

Usage:
    python launcher.py                  # Dev mode
    GOST-BI.exe                         # Compiled EXE (double-click)
    GOST-BI.exe --port 8088             # Custom port
    GOST-BI.exe --no-browser            # Don't open browser
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def find_free_port(start: int = 8088) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start


def main() -> int:
    parser = argparse.ArgumentParser(description="GOST BI Launcher")
    parser.add_argument("--port", type=int, default=0, help="Server port (0 = auto)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind address")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    args = parser.parse_args()

    port = args.port if args.port else find_free_port()
    url = f"http://{args.host}:{port}"

    print("=" * 56)
    print("  GOST BI — Russian BI Platform")
    print(f"  Version: 0.1.0")
    print(f"  Address: {url}")
    print("=" * 56)
    print()

    os.environ["GOST_BI_PORT"] = str(port)
    os.environ["GOST_BI_HOST"] = args.host

    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

    import uvicorn

    if not args.no_browser:
        def open_browser():
            time.sleep(1.5)
            webbrowser.open(url)
        threading.Thread(target=open_browser, daemon=True).start()

    print(f"Server starting at {url}")
    print(f"API docs:    {url}/api/docs")
    print(f"Health:      {url}/api/health")
    print("Press Ctrl+C to stop.")
    print()

    uvicorn.run(
        "gost_bi.core.app:app",
        host=args.host,
        port=port,
        log_level="info",
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
