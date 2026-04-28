from __future__ import annotations

from app.adapters.storage import StorageAdapter
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.models.domain import UploadRecord


class UploadService:
    def __init__(self, storage: StorageAdapter, settings: Settings) -> None:
        self.storage = storage
        self.settings = settings

    def init_upload(self, filename: str, content_type: str) -> UploadRecord:
        return self.storage.init_upload(
            filename=filename,
            content_type=content_type,
            ttl_minutes=self.settings.upload_url_ttl_minutes,
        )

    def complete_upload(
        self,
        upload_id: str,
        *,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> UploadRecord:
        return self.storage.complete_upload(
            upload_id,
            filename=filename,
            content_type=content_type,
            data=data,
        )

    def ensure_source_exists(self, artifact_uri: str) -> None:
        if not self.storage.artifact_exists(artifact_uri):
            raise NotFoundError(f"Source artifact '{artifact_uri}' was not found.")

