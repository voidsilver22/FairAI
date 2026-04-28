from __future__ import annotations

from threading import RLock
from uuid import uuid4

from app.core.exceptions import NotFoundError
from app.ml.utils import utc_now
from app.models.domain import AsyncJobRecord
from app.models.enums import JobStatus


class InMemoryJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, AsyncJobRecord] = {}
        self._lock = RLock()

    def create_job(
        self,
        *,
        file_uri: str,
        config: dict,
        job_id: str | None = None,
    ) -> AsyncJobRecord:
        timestamp = utc_now()
        record = AsyncJobRecord(
            job_id=job_id or str(uuid4()),
            status=JobStatus.PENDING,
            file_uri=file_uri,
            config=config,
            created_at=timestamp,
            updated_at=timestamp,
        )
        with self._lock:
            self._jobs[record.job_id] = record
        return record

    def update_job(self, job_id: str, **updates) -> AsyncJobRecord:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                raise NotFoundError(f"Job '{job_id}' was not found.")

            updates["updated_at"] = utc_now()
            if updates.get("status") == JobStatus.RUNNING and record.started_at is None:
                updates.setdefault("started_at", updates["updated_at"])
            if updates.get("status") in {JobStatus.COMPLETED, JobStatus.FAILED}:
                updates.setdefault("completed_at", updates["updated_at"])

            updated = record.model_copy(update=updates)
            self._jobs[job_id] = updated
            return updated

    def get_job(self, job_id: str) -> AsyncJobRecord:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                raise NotFoundError(f"Job '{job_id}' was not found.")
            return record

    def list_jobs(self) -> list[AsyncJobRecord]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda job: job.created_at)
