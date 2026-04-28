from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.ml.utils import utc_now
from app.schemas.common import HealthResponse
from app.services.runtime import ApplicationContainer

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(container: ApplicationContainer = Depends(get_container)) -> HealthResponse:
    settings = container.settings
    return HealthResponse(
        status="ok",
        environment=settings.environment,
        storage_backend=container.storage.backend_name,
        queue_backend=container.queue.backend_name,
        compute_backend=container.compute.backend_name,
        time=utc_now(),
    )
