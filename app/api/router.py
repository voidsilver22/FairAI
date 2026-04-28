from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import health, hosted, jobs, metadata, metrics, uploads


api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(metadata.router, tags=["metadata"])
api_router.include_router(metrics.router, tags=["metrics"])
api_router.include_router(uploads.router, tags=["uploads"])
api_router.include_router(jobs.router, tags=["jobs"])
api_router.include_router(hosted.router, tags=["hosted"])

