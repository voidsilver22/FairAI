from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.adapters.compute import ComputeAdapter, build_compute_adapter
from app.adapters.queue import QueueAdapter, build_queue_adapter
from app.adapters.storage import StorageAdapter, build_storage_adapter
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.ml.pipeline import FairLensPipeline
from app.services.artifact_service import ArtifactService
from app.services.job_service import JobService
from app.services.job_store import InMemoryJobStore
from app.services.orchestration import JobOrchestrator
from app.services.reporting_service import ReportingService
from app.services.repositories import FileJobRepository
from app.services.upload_service import UploadService


@dataclass(slots=True)
class ApplicationContainer:
    settings: Settings
    storage: StorageAdapter
    queue: QueueAdapter
    compute: ComputeAdapter
    job_store: InMemoryJobStore
    repository: FileJobRepository
    artifact_service: ArtifactService
    upload_service: UploadService
    reporting_service: ReportingService
    pipeline: FairLensPipeline
    orchestrator: JobOrchestrator
    job_service: JobService


@lru_cache(maxsize=1)
def get_application_container() -> ApplicationContainer:
    settings = get_settings()
    configure_logging(settings)
    storage = build_storage_adapter(settings)
    queue = build_queue_adapter(settings)
    compute = build_compute_adapter(settings)
    job_store = InMemoryJobStore()
    repository = FileJobRepository(settings.resolved_storage_root() / "jobs")
    artifact_service = ArtifactService(storage, settings)
    upload_service = UploadService(storage, settings)
    reporting_service = ReportingService()
    pipeline = FairLensPipeline(
        counterfactual_sample_size=settings.max_counterfactual_samples,
    )
    orchestrator = JobOrchestrator(
        repository=repository,
        job_store=job_store,
        artifact_service=artifact_service,
        reporting_service=reporting_service,
        pipeline=pipeline,
        queue_adapter=queue,
        compute_adapter=compute,
    )
    job_service = JobService(
        settings=settings,
        repository=repository,
        job_store=job_store,
        upload_service=upload_service,
        artifact_service=artifact_service,
        orchestrator=orchestrator,
    )
    return ApplicationContainer(
        settings=settings,
        storage=storage,
        queue=queue,
        compute=compute,
        job_store=job_store,
        repository=repository,
        artifact_service=artifact_service,
        upload_service=upload_service,
        reporting_service=reporting_service,
        pipeline=pipeline,
        orchestrator=orchestrator,
        job_service=job_service,
    )


def reset_application_container() -> None:
    get_application_container.cache_clear()
