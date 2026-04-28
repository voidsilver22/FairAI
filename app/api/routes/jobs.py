from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from app.api.dependencies import get_container
from app.models.enums import ArtifactKind
from app.schemas.jobs import (
    DebiasJobRequest,
    InlinePipelineRequest,
    InlinePipelineResponse,
    JobAcceptedResponse,
    JobListResponse,
    JobStatusResponse,
    JobSubmitRequest,
    JobSubmitResponse,
)
from app.schemas.reports import ArtifactDownloadResponse, FairnessReportResponse
from app.services.runtime import ApplicationContainer

router = APIRouter()


@router.post(
    "/jobs/debias",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_debias_job(
    payload: DebiasJobRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    container: ApplicationContainer = Depends(get_container),
) -> JobAcceptedResponse:
    input_spec = payload.to_input_spec(container.settings.default_fairness_weight)
    job = container.job_service.create_job(input_spec)
    background_tasks.add_task(container.job_service.enqueue_job, job.job_id)
    return JobAcceptedResponse(
        job_id=job.job_id,
        status_url=str(request.url_for("get_job_status", job_id=job.job_id)),
    )


@router.post("/jobs", response_model=JobSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_job_compat(
    payload: JobSubmitRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    container: ApplicationContainer = Depends(get_container),
) -> JobSubmitResponse:
    debias_request = payload.to_debias_request()
    input_spec = debias_request.to_input_spec(container.settings.default_fairness_weight)
    job = container.job_service.create_job(input_spec)
    background_tasks.add_task(container.job_service.enqueue_job, job.job_id)
    return JobSubmitResponse(
        job_id=job.job_id,
        status_url=str(request.url_for("get_job_status", job_id=job.job_id)),
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse, name="get_job_status")
async def get_job_status(
    job_id: str,
    container: ApplicationContainer = Depends(get_container),
) -> JobStatusResponse:
    return JobStatusResponse(job=container.job_service.get_job(job_id))


@router.get("/jobs", response_model=JobListResponse, name="list_jobs")
async def list_jobs(
    container: ApplicationContainer = Depends(get_container),
) -> JobListResponse:
    return JobListResponse(jobs=container.job_service.list_jobs())


@router.get("/jobs/{job_id}/report", response_model=FairnessReportResponse, name="get_job_report")
async def get_job_report(
    job_id: str,
    container: ApplicationContainer = Depends(get_container),
) -> FairnessReportResponse:
    return FairnessReportResponse(report=container.job_service.get_report(job_id))


@router.get("/jobs/{job_id}/artifacts/{artifact_kind}", response_model=ArtifactDownloadResponse)
async def get_artifact_download(
    job_id: str,
    artifact_kind: ArtifactKind,
    container: ApplicationContainer = Depends(get_container),
) -> ArtifactDownloadResponse:
    return container.job_service.get_artifact_download(job_id, artifact_kind)


@router.post(
    "/pipeline/execute",
    response_model=InlinePipelineResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def execute_pipeline_inline(
    payload: InlinePipelineRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    container: ApplicationContainer = Depends(get_container),
) -> InlinePipelineResponse:
    input_spec = payload.to_input_spec(container.settings.default_fairness_weight)
    job = container.job_service.create_inline_job(
        input_spec=input_spec,
        records=payload.records,
    )
    background_tasks.add_task(container.job_service.enqueue_job, job.job_id)
    return InlinePipelineResponse(
        job_id=job.job_id,
        status_url=str(request.url_for("get_job_status", job_id=job.job_id)),
    )

@router.delete("/jobs", status_code=200)
def clear_jobs(container: ApplicationContainer = Depends(get_container)) -> dict:
    """Clear all jobs from the job store."""
    if hasattr(container.job_store, "_jobs"):
        with container.job_store._lock:
            container.job_store._jobs.clear()
    return {"status": "ok"}
