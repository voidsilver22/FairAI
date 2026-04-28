from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.ml.metrics import list_metric_definitions
from app.schemas.common import MetadataResponse
from app.services.runtime import ApplicationContainer

router = APIRouter()


@router.get("/metadata", response_model=MetadataResponse)
async def metadata(container: ApplicationContainer = Depends(get_container)) -> MetadataResponse:
    settings = container.settings
    return MetadataResponse(
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        supported_metrics=len(list_metric_definitions()),
        execution_modes=["queued"],
        adapters={
            "storage": container.storage.backend_name,
            "queue": container.queue.backend_name,
            "compute": container.compute.backend_name,
        },
        optional_integrations={
            "gcp_project": settings.gcp_project,
            "dlp_enabled": settings.dlp_enabled,
            "future_hosted_api": True,
            "model_training_workspace": str(settings.resolved_model_training_workspace()),
            "model_training_workspace_present": container.model_training_service.workspace.exists(),
            "model_training_capabilities": container.model_training_service.describe_workspace()[
                "capabilities"
            ],
        },
    )
