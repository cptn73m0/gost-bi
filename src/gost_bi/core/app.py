"""
GOST BI — Core FastAPI Application.

Entry point that serves:
- REST API (health, config, dashboards, SQL, GOST)
- Frontend SPA (React build via static files in dev mode)
- WebSocket endpoint for real-time dashboard updates
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from gost_bi.core.auth import get_current_user, require_analyst, API_KEYS

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend"
FRONTEND_BUILD = FRONTEND_DIR / "dist"

app = FastAPI(
    title="GOST BI",
    description="Российская BI-платформа на базе Apache Superset с AI-ускорением",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_BUILD.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_BUILD / "assets")), name="assets")


# ============================================================
# Health (Level 11)
# ============================================================

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "components": {
            "api": "ok",
            "sql_verifier": "ok",
            "gost_templates": str(len(BUILTIN_TEMPLATES)) if "BUILTIN_TEMPLATES" in dir() else "ok",
        },
    }


@app.get("/api/health/ready")
async def readiness_check():
    return {"status": "ready"}


@app.get("/api/health/live")
async def liveness_check():
    return {"status": "alive"}


# ============================================================
# Auth-protected API
# ============================================================

@app.get("/api/me")
async def current_user_info(user=Depends(get_current_user)):
    return {
        "id": user.id,
        "login": user.login,
        "full_name": user.full_name,
        "email": user.email,
        "roles": [r.value for r in user.roles],
        "organization": user.organization,
    }


@app.get("/api/dashboards")
async def list_dashboards(user=Depends(require_analyst)):
    return {
        "dashboards": [
            {"id": "main", "name": "Главная", "widgets": 6},
            {"id": "sales", "name": "Продажи", "widgets": 4},
            {"id": "finance", "name": "Финансы", "widgets": 3},
        ]
    }


# ============================================================
# WebSocket
# ============================================================

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    from gost_bi.core.websocket import hub
    await hub.handle_client(websocket, client_id)


# ============================================================
# Theme & Configuration
# ============================================================

@app.get("/api/config")
async def app_config():
    return {
        "name": "ГОСТ БИ",
        "version": "0.1.0",
        "language": "ru",
        "date_format": "DD.MM.YYYY",
        "currency": "₽",
        "features": {
            "sql_lab": True,
            "nlp_sql": True,
            "gost_reports": True,
            "dark_mode": True,
        },
    }


# ============================================================
# Frontend SPA
# ============================================================

@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_spa(request: Request, full_path: str):
    index_path = FRONTEND_BUILD / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    return HTMLResponse(
        """<!DOCTYPE html>
<html lang="ru">
<head><meta charset="utf-8"><title>ГОСТ БИ</title></head>
<body style="font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;color:#44546f;">
<div style="text-align:center"><h1>ГОСТ БИ</h1><p>Фронтенд не собран. Запустите <code>cd frontend && npm run build</code></p></div>
</body></html>"""
    )
