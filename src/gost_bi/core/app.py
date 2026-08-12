"""
Core FastAPI application stub.

This will become the main entry point after Superset fork integration.
Currently provides:
- Health check endpoint (Level 11)
- Basic API structure
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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


@app.get("/api/health")
async def health_check():
    """Level 11: Health check endpoint for Kubernetes and monitoring."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "components": {
            "api": "ok",
        },
    }


@app.get("/api/health/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    # TODO: check DB, Redis, Celery connectivity
    return {"status": "ready"}


@app.get("/api/health/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"status": "alive"}
