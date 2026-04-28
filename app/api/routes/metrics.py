from __future__ import annotations

from fastapi import APIRouter

from app.ml.metrics import list_metric_definitions
from app.schemas.metrics import MetricCatalogResponse

router = APIRouter()


@router.get("/metrics", response_model=MetricCatalogResponse)
async def metrics() -> MetricCatalogResponse:
    return MetricCatalogResponse(metrics=list_metric_definitions())
