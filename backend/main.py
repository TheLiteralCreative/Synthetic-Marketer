"""FastAPI app entry — mounts API routes and serves the React frontend.

Usage:
    uvicorn backend.main:app --reload   # dev
    python start.py                     # production-ish (via launcher)
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import __version__
from backend.routes import router as api_router

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = ROOT / "frontend" / "dist"

app = FastAPI(
    title="Synthetic-Marketer",
    version=__version__,
    description="Local-first marketing audit pipeline.",
)

# CORS for dev mode (frontend on :5173, backend on :8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api")
def api_root() -> dict:
    return {
        "name": "Synthetic-Marketer",
        "version": __version__,
        "docs": "/docs",
        "health": "/api/ping",
    }


# --- Static frontend (production build) ---
if FRONTEND_DIST.exists():
    # Serve assets/ at the path expected by Vite's default build
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        # API routes already matched above. Anything else falls back to index.html
        # so React Router can handle client-side routes.
        candidate = FRONTEND_DIST / path
        if path and candidate.is_file():
            return FileResponse(str(candidate))
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return JSONResponse(
            {"error": "frontend not built", "hint": "run npm install && npm run build in frontend/"},
            status_code=503,
        )
else:
    @app.get("/")
    def root_no_build() -> JSONResponse:
        return JSONResponse(
            {
                "error": "frontend not built",
                "hint": "cd frontend && npm install && npm run build, then python start.py",
                "api": "/api/ping",
            },
            status_code=503,
        )
