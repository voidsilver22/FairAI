from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.schemas.model_training import (
    ModelTrainingAuditRequest,
    ModelTrainingAuditResponse,
    ModelTrainingDatasetBuildRequest,
    ModelTrainingDatasetBuildResponse,
    ModelTrainingWorkspaceResponse,
)
from app.services.runtime import ApplicationContainer

router = APIRouter()


@router.get("/model-training", response_model=ModelTrainingWorkspaceResponse)
async def model_training_workspace(
    container: ApplicationContainer = Depends(get_container),
) -> ModelTrainingWorkspaceResponse:
    return ModelTrainingWorkspaceResponse.model_validate(
        container.model_training_service.describe_workspace()
    )


@router.post("/model-training/dataset", response_model=ModelTrainingDatasetBuildResponse)
async def build_model_training_dataset(
    payload: ModelTrainingDatasetBuildRequest,
    container: ApplicationContainer = Depends(get_container),
) -> ModelTrainingDatasetBuildResponse:
    return ModelTrainingDatasetBuildResponse.model_validate(
        container.model_training_service.build_unstructured_dataset(
            input_filename=payload.input_filename,
            output_filename=payload.output_filename,
        )
    )


@router.post("/model-training/audit", response_model=ModelTrainingAuditResponse)
async def run_model_training_audit(
    payload: ModelTrainingAuditRequest,
    container: ApplicationContainer = Depends(get_container),
) -> ModelTrainingAuditResponse:
    return ModelTrainingAuditResponse.model_validate(
        container.model_training_service.run_workspace_audit(
            baseline_results_filename=payload.baseline_results_filename,
            fairlens_results_filename=payload.fairlens_results_filename,
            baseline_score_column=payload.baseline_score_column,
            fairlens_score_column=payload.fairlens_score_column,
            baseline_threshold=payload.baseline_threshold,
            fairlens_threshold=payload.fairlens_threshold,
            output_filename=payload.output_filename,
        )
    )
