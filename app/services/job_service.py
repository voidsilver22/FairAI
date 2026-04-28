from __future__ import annotations

import io
import json
from uuid import uuid4

import pandas as pd

from app.core.config import Settings
from app.core.exceptions import InvalidStateError
from app.ml.baseline import LinearModelState
from app.ml.features import FeatureExtractor
from app.ml.scrubber import ResumeScrubber
from app.ml.utils import utc_now
from app.models.domain import (
    AsyncJobRecord,
    AuditInputSpec,
    AuditJobRecord,
    FairnessReport,
    LinearModelArtifact,
    StatusEvent,
)
from app.models.enums import ArtifactKind, JobStatus, PipelineStage
from app.schemas.hosted import HostedScoreResponse
from app.services.artifact_service import ArtifactService
from app.services.job_store import InMemoryJobStore
from app.services.orchestration import JobOrchestrator
from app.services.repositories import FileJobRepository
from app.services.upload_service import UploadService


class JobService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: FileJobRepository,
        job_store: InMemoryJobStore,
        upload_service: UploadService,
        artifact_service: ArtifactService,
        orchestrator: JobOrchestrator,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.job_store = job_store
        self.upload_service = upload_service
        self.artifact_service = artifact_service
        self.orchestrator = orchestrator
        self.scrubber = ResumeScrubber()
        self.feature_extractor = FeatureExtractor()

    def create_job(self, input_spec: AuditInputSpec) -> AsyncJobRecord:
        if input_spec.source_uri is None:
            raise InvalidStateError("A debias job requires a source file URI.")
        self.upload_service.ensure_source_exists(input_spec.source_uri)

        job_id = str(uuid4())
        timestamp = utc_now()
        stored_job = self.job_store.create_job(
            job_id=job_id,
            file_uri=input_spec.source_uri,
            config=input_spec.model_dump(mode="json"),
        )
        record = AuditJobRecord(
            job_id=job_id,
            created_at=timestamp,
            updated_at=timestamp,
            status=JobStatus.PENDING,
            stage=PipelineStage.RECEIVED,
            input_spec=input_spec,
            status_history=[
                StatusEvent(
                    status=JobStatus.PENDING,
                    stage=PipelineStage.RECEIVED,
                    message="Job accepted by API.",
                    timestamp=timestamp,
                )
            ],
        )
        self.repository.save(record)
        return stored_job

    def create_inline_job(
        self,
        *,
        input_spec: AuditInputSpec,
        records: list[dict],
    ) -> AsyncJobRecord:
        file_id = f"inline-{uuid4()}"
        frame = pd.DataFrame.from_records(records)
        buffer = io.StringIO()
        frame.to_csv(buffer, index=False)
        file_uri = self.artifact_service.storage.save_file(
            file_id=file_id,
            filename="inline_records.csv",
            content_type="text/csv",
            data=buffer.getvalue().encode("utf-8"),
            namespace="inline/jobs",
        )
        return self.create_job(input_spec.model_copy(update={"source_uri": file_uri}))

    async def enqueue_job(self, job_id: str) -> dict:
        return self.orchestrator.enqueue_job(job_id)

    def get_job(self, job_id: str) -> AsyncJobRecord:
        return self.job_store.get_job(job_id)

    def list_jobs(self) -> list[AsyncJobRecord]:
        return self.job_store.list_jobs()

    def get_report(self, job_id: str) -> FairnessReport:
        job = self.repository.get(job_id)
        if job.report is None:
            raise InvalidStateError("Job report is not available yet.")
        return job.report

    def get_artifact_download(self, job_id: str, kind: ArtifactKind):
        job = self.repository.get(job_id)
        artifact = self.artifact_service.find_artifact(job, kind)
        return self.artifact_service.build_download_response(artifact)

    def score_hosted_resume(self, job_id: str, resume_text: str) -> HostedScoreResponse:
        job = self.repository.get(job_id)
        if job.status != JobStatus.COMPLETED:
            raise InvalidStateError("Hosted scoring requires a completed verification job.")

        model_artifact = self.artifact_service.find_artifact(job, ArtifactKind.DEBIASED_MODEL)
        artifact_bytes = self.artifact_service.storage.read_bytes(model_artifact.artifact_uri)
        model = LinearModelState.from_artifact(
            LinearModelArtifact.model_validate(json.loads(artifact_bytes.decode("utf-8")))
        )
        scoring_frame = pd.DataFrame(
            [
                {
                    "__resume_text": resume_text,
                    **{
                        protected_attribute: "unknown"
                        for protected_attribute in job.input_spec.protected_attributes
                    },
                }
            ]
        )
        scrubbed = self.scrubber.scrub_frame(scoring_frame, "__resume_text")
        feature_result = self.feature_extractor.build_features(
            scrubbed.frame,
            text_column="__scrubbed_text",
            label_column=job.input_spec.label_column,
            protected_attributes=job.input_spec.protected_attributes,
            include_protected_attributes=False,
        )
        probability = float(model.predict_probabilities(feature_result.features)[0])
        prediction = int(probability >= 0.5)
        return HostedScoreResponse(
            job_id=job_id,
            score=round(probability, 4),
            prediction=prediction,
            model_name=model.model_name,
            notes=[
                "Hosted scoring uses the latest debiased verification model from the selected audit job.",
                "Protected attributes are not supplied at request time in local hosted mode.",
            ],
        )
