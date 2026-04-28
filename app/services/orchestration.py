from __future__ import annotations

from typing import Callable

from app.adapters.compute import ComputeAdapter
from app.adapters.queue import QueueAdapter
from app.core.exceptions import FairLensError
from app.ml.pipeline import FairLensPipeline, PipelineRequest, PipelineRunOutput
from app.ml.utils import utc_now
from app.models.domain import AuditInputSpec, AuditJobRecord, FairnessReport, StatusEvent
from app.models.enums import ArtifactKind, JobStatus, PipelineStage
from app.services.artifact_service import ArtifactService
from app.services.job_store import InMemoryJobStore
from app.services.reporting_service import ReportingService
from app.services.repositories import FileJobRepository
from app.workers.payloads import JobExecutionMessage


class JobOrchestrator:
    def __init__(
        self,
        *,
        repository: FileJobRepository,
        job_store: InMemoryJobStore,
        artifact_service: ArtifactService,
        reporting_service: ReportingService,
        pipeline: FairLensPipeline,
        queue_adapter: QueueAdapter,
        compute_adapter: ComputeAdapter,
    ) -> None:
        self.repository = repository
        self.job_store = job_store
        self.artifact_service = artifact_service
        self.reporting_service = reporting_service
        self.pipeline = pipeline
        self.queue_adapter = queue_adapter
        self.compute_adapter = compute_adapter
        self.queue_adapter.subscribe_jobs(self._handle_queue_message)

    def enqueue_job(self, job_id: str) -> dict:
        job = self.job_store.get_job(job_id)
        message = JobExecutionMessage(
            job_id=job_id,
            file_uri=job.file_uri,
            config=job.config,
            requested_at=utc_now(),
        )
        publish_result = self.queue_adapter.publish_job(message.model_dump(mode="json"))

        persisted = self.repository.get(job_id)
        persisted.cloud_hooks["queue"] = publish_result
        self.repository.save(persisted)
        return publish_result

    def run_job(self, job_id: str, payload: dict) -> AuditJobRecord:
        request = PipelineRequest(
            job_id=job_id,
            file_uri=str(payload["file_uri"]),
            config=AuditInputSpec.model_validate(payload["config"]),
        )
        self.job_store.update_job(job_id, status=JobStatus.RUNNING, error=None, result=None)

        job = self.repository.get(job_id)
        self._append_event(job, JobStatus.RUNNING, PipelineStage.INGESTION, "Worker picked up job.")
        job.input_spec = request.config
        job.input_spec.source_uri = request.file_uri
        job.cloud_hooks.setdefault("compute", self._build_compute_hook(job_id, request.file_uri, request.config))
        self.repository.save(job)

        try:
            output = self.pipeline.execute(
                request=request,
                data_loader=self.artifact_service.load_dataframe,
                progress_callback=self._progress_callback(job_id),
            )
            completed = self._persist_output(job, output)
            
            # Include the full report in the job_store result for the frontend
            job_result = output.to_job_result()
            job_result["report"] = output.report.model_dump(mode="json")
            
            self.job_store.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                result=job_result,
                error=None,
            )
            return completed
        except Exception as error:
            failed = self.repository.get(job_id)
            failed.status = JobStatus.FAILED
            failed.stage = PipelineStage.FAILED
            failed.updated_at = utc_now()
            failed.error_message = str(error)
            failed.status_history.append(
                StatusEvent(
                    status=JobStatus.FAILED,
                    stage=PipelineStage.FAILED,
                    message=str(error),
                    timestamp=utc_now(),
                )
            )
            self.repository.save(failed)
            self.job_store.update_job(job_id, status=JobStatus.FAILED, error=str(error), result=None)
            if isinstance(error, FairLensError):
                raise
            raise

    def run_inline_report(
        self,
        *,
        frame,
        job_id: str,
        input_spec,
    ) -> FairnessReport:
        output = self.pipeline.run(job_id=job_id, frame=frame, spec=input_spec)
        return output.report

    def _handle_queue_message(self, payload: dict) -> None:
        message = JobExecutionMessage.model_validate(payload)
        self.run_job(
            message.job_id,
            {
                "file_uri": message.file_uri,
                "config": message.config,
            },
        )

    def _persist_output(self, job: AuditJobRecord, output: PipelineRunOutput) -> AuditJobRecord:
        report_json = output.report.model_dump(mode="json")
        report_markdown = self.reporting_service.build_markdown_report(output.report)

        artifacts = [
            self.artifact_service.save_dataframe(
                job_id=job.job_id,
                kind=ArtifactKind.SCRUBBED_DATASET,
                frame=output.artifacts.scrubbed_frame,
                filename="scrubbed_dataset.csv",
                description="Scrubbed resume dataset with proxy masking annotations.",
            ),
            self.artifact_service.save_dataframe(
                job_id=job.job_id,
                kind=ArtifactKind.FEATURE_FRAME,
                frame=output.artifacts.verification_feature_frame,
                filename="verification_features.csv",
                description="Verification-stage feature matrix.",
            ),
            self.artifact_service.save_model(
                job_id=job.job_id,
                kind=ArtifactKind.BASELINE_MODEL,
                model=output.artifacts.baseline_model,
                filename="baseline_model.json",
                description="Baseline predictor artifact.",
            ),
            self.artifact_service.save_model(
                job_id=job.job_id,
                kind=ArtifactKind.DEBIASED_MODEL,
                model=output.artifacts.debiased_model,
                filename="debiased_model.json",
                description="Debiased predictor artifact.",
            ),
            self.artifact_service.save_json(
                job_id=job.job_id,
                kind=ArtifactKind.BASELINE_REPORT,
                payload={
                    "metrics": [
                        metric.model_dump(mode="json")
                        for metric in output.report.baseline_metrics
                    ]
                },
                filename="baseline_report.json",
                description="Baseline fairness metrics.",
            ),
            self.artifact_service.save_json(
                job_id=job.job_id,
                kind=ArtifactKind.VERIFICATION_REPORT,
                payload={
                    "metrics": [
                        metric.model_dump(mode="json")
                        for metric in output.report.verification_metrics
                    ]
                },
                filename="verification_report.json",
                description="Verification fairness metrics.",
            ),
            self.artifact_service.save_json(
                job_id=job.job_id,
                kind=ArtifactKind.REPORT_JSON,
                payload=report_json,
                filename="report.json",
                description="Full structured fairness report.",
            ),
            self.artifact_service.save_text(
                job_id=job.job_id,
                kind=ArtifactKind.REPORT_MARKDOWN,
                content=report_markdown,
                filename="report.md",
                description="Human-readable fairness report.",
            ),
        ]

        job.report = output.report.model_copy(update={"cloud_hooks": job.cloud_hooks})
        job.artifacts.extend(artifacts)
        self._append_event(job, JobStatus.COMPLETED, PipelineStage.COMPLETED, "Audit job completed.")
        self.repository.save(job)
        return job

    def _progress_callback(self, job_id: str) -> Callable[[PipelineStage, str], None]:
        def callback(stage: PipelineStage, message: str) -> None:
            job = self.repository.get(job_id)
            self._append_event(job, JobStatus.RUNNING, stage, message)
            self.repository.save(job)

        return callback

    def _build_compute_hook(
        self,
        job_id: str,
        file_uri: str,
        spec: AuditInputSpec,
    ) -> dict:
        if self.compute_adapter.backend_name == "local":
            return self.compute_adapter.submit_audit_job(
                job_id,
                {
                    "file_uri": file_uri,
                    "label_column": spec.label_column,
                },
            )
        return {
            "backend": self.compute_adapter.backend_name,
            "mode": "stubbed",
            "ready_for_remote_execution": True,
        }

    @staticmethod
    def _append_event(
        job: AuditJobRecord,
        status: JobStatus,
        stage: PipelineStage,
        message: str,
    ) -> None:
        timestamp = utc_now()
        job.status = status
        job.stage = stage
        job.updated_at = timestamp
        job.status_history.append(
            StatusEvent(
                status=status,
                stage=stage,
                message=message,
                timestamp=timestamp,
            )
        )
