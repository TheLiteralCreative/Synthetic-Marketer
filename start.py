#!/usr/bin/env python3
"""Synthetic-Marketer launcher.

Usage:
    python start.py            # production mode: build frontend (if needed) + serve
    python start.py --dev      # dev mode: skip build, frontend runs on Vite at :5173
    python start.py --no-open  # don't auto-open browser

Default URL: http://localhost:8000
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"
PORT = 8000


def ensure_python_deps() -> None:
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError:
        print("ERROR: backend dependencies missing.", file=sys.stderr)
        print("Run: pip install -e .", file=sys.stderr)
        print("(or:  pip install fastapi 'uvicorn[standard]' pydantic python-multipart)",
              file=sys.stderr)
        sys.exit(1)


def ensure_frontend_built(force: bool = False) -> None:
    if DIST_DIR.exists() and (DIST_DIR / "index.html").exists() and not force:
        return
    if not shutil.which("npm"):
        print("ERROR: npm not found. Install Node.js (https://nodejs.org).", file=sys.stderr)
        sys.exit(1)

    node_modules = FRONTEND_DIR / "node_modules"
    if not node_modules.exists():
        print("[start] Installing frontend dependencies (npm install)...")
        subprocess.run(["npm", "install"], cwd=FRONTEND_DIR, check=True)

    print("[start] Building frontend (npm run build)...")
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, check=True)


def open_browser_after_delay(url: str, delay: float = 1.5) -> None:
    def _go():
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=_go, daemon=True).start()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dev", action="store_true", help="Run uvicorn with --reload, skip frontend build")
    ap.add_argument("--rebuild", action="store_true", help="Force frontend rebuild even if dist/ exists")
    ap.add_argument("--no-open", action="store_true", help="Don't auto-open the browser")
    ap.add_argument("--port", type=int, default=PORT, help=f"Port (default: {PORT})")
    args = ap.parse_args()

    ensure_python_deps()

    if args.dev:
        print("[start] Dev mode — backend only. Run `npm run dev` in frontend/ separately.")
    else:
        ensure_frontend_built(force=args.rebuild)

    url = f"http://localhost:{args.port}"
    if not args.no_open:
        open_browser_after_delay(url)

    print(f"[start] Synthetic-Marketer running at {url}")
    print("[start] Press Ctrl+C to stop.")

    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=args.port,
        reload=args.dev,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
