from __future__ import annotations

from pathlib import Path
from threading import Lock

from app.core.exceptions import NotFoundError
from app.models.domain import AuditJobRecord


class FileJobRepository:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def save(self, job: AuditJobRecord) -> AuditJobRecord:
        with self._lock:
            path = self.root / f"{job.job_id}.json"
            temp_path = path.with_suffix(".json.tmp")
            temp_path.write_text(job.model_dump_json(indent=2), encoding="utf-8")
            temp_path.replace(path)
        return job

    def get(self, job_id: str) -> AuditJobRecord:
        with self._lock:
            path = self.root / f"{job_id}.json"
            if not path.exists():
                raise NotFoundError(f"Job '{job_id}' was not found.")
            return AuditJobRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def list(self) -> list[AuditJobRecord]:
        jobs: list[AuditJobRecord] = []
        for path in sorted(self.root.glob("*.json")):
            jobs.append(AuditJobRecord.model_validate_json(path.read_text(encoding="utf-8")))
        return jobs
