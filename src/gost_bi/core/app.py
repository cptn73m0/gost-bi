"""
GOST BI — Core FastAPI Application.

Entry point that serves:
- REST API (health, config, dashboards, SQL, GOST)
- Frontend SPA (React build via static files in dev mode)
- WebSocket endpoint for real-time dashboard updates
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from gost_bi.core.auth import get_current_user, require_analyst, require_admin, API_KEYS


def _get_frontend_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent.parent.parent.parent
    return base / "frontend"

FRONTEND_DIR = _get_frontend_dir()
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

class SQLQueryRequest(BaseModel):
    sql: str


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
# Auth endpoints
# ============================================================

class LoginRequest(BaseModel):
    login: str
    password: str


class RegisterRequest(BaseModel):
    login: str
    password: str
    full_name: str
    role: str = "viewer"


@app.post("/api/auth/login")
async def login(req: LoginRequest, request: Request):
    from gost_bi.core.auth_service import authenticate
    ip = request.client.host if request.client else ""
    result = authenticate(req.login, req.password, ip)
    if not result:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return result


@app.post("/api/auth/register")
async def register(req: RegisterRequest, user=Depends(require_admin)):
    from gost_bi.core.auth_service import register_user
    result = register_user(req.login, req.password, req.full_name, req.role)
    if not result:
        raise HTTPException(status_code=400, detail="Не удалось создать пользователя")
    return result


@app.get("/api/auth/setup-status")
async def setup_status():
    from gost_bi.core.auth_service import has_admin
    return {"has_admin": has_admin()}


@app.post("/api/auth/setup")
async def setup_admin(req: RegisterRequest):
    from gost_bi.core.auth_service import has_admin, register_user
    if has_admin():
        raise HTTPException(status_code=400, detail="Администратор уже существует")
    result = register_user(req.login, req.password, req.full_name, "admin")
    if not result:
        raise HTTPException(status_code=400, detail="Не удалось создать администратора")
    return result


@app.get("/api/auth/users")
async def list_users_endpoint(user=Depends(require_admin)):
    from gost_bi.core.auth_service import list_users
    return {"users": list_users()}


@app.get("/api/auth/audit")
async def audit_log_endpoint(user=Depends(require_admin), limit: int = 100):
    from gost_bi.core.auth_service import get_audit_log
    return {"entries": get_audit_log(limit)}


# ============================================================
# Database
# ============================================================

DB_URL = "postgresql://gostbi:gostbi@localhost:5432/gostbi"


def _get_db_engine():
    import os
    from sqlalchemy import create_engine
    url = os.environ.get("DATABASE_URL", DB_URL)
    return create_engine(url, connect_args={"connect_timeout": 3})


@app.get("/api/db/status")
async def db_status(user=Depends(require_analyst)):
    try:
        engine = _get_db_engine()
        with engine.connect() as conn:
            tables = conn.exec_driver_sql(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
            ).fetchall()
            counts = {}
            for (tbl,) in tables:
                cnt = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {tbl}").scalar()
                counts[tbl] = cnt
        return {"status": "connected", "tables": counts}
    except Exception as exc:
        return {"status": "disconnected", "error": str(exc)}


@app.post("/api/db/query")
async def execute_query(req: SQLQueryRequest, user=Depends(require_analyst)):
    from gost_bi.quality.sql_verifier import SQLVerifier

    verifier = SQLVerifier()
    report = verifier.verify(req.sql, nlp_input="API query", model="manual")
    report.log()

    if not report.overall_passed:
        errors = [c.message for c in report.checks if not c.passed]
        raise HTTPException(status_code=400, detail=f"SQL blocked: {'; '.join(errors)}")

    try:
        engine = _get_db_engine()
        with engine.connect() as conn:
            result = conn.exec_driver_sql(req.sql)
            rows = [dict(row._mapping) for row in result.fetchall()]
        return {"status": "ok", "rows": rows, "count": len(rows)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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
        content = index_path.read_text(encoding="utf-8")
        return HTMLResponse(content)
    return HTMLResponse(
        """<!DOCTYPE html>
<html lang="ru">
<head><meta charset="utf-8"><title>GOST BI</title></head>
<body style="font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;color:#44546f;">
<div style="text-align:center"><h1>GOST BI</h1><p>Frontend not built. Run: cd frontend && npm run build</p></div>
</body></html>"""
    )
