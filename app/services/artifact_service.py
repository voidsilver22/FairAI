from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any

import pandas as pd

from app.adapters.storage import StorageAdapter
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.models.domain import ArtifactRecord, AuditJobRecord, LinearModelArtifact
from app.models.enums import ArtifactKind
from app.schemas.reports import ArtifactDownloadResponse


class ArtifactService:
    def __init__(self, storage: StorageAdapter, settings: Settings) -> None:
        self.storage = storage
        self.settings = settings

    def load_dataframe(self, artifact_uri: str) -> pd.DataFrame:
        raw = self.storage.read_bytes(artifact_uri)
        if artifact_uri.endswith(".parquet"):
            return pd.read_parquet(io.BytesIO(raw))
        return pd.read_csv(io.BytesIO(raw))

    def save_dataframe(
        self,
        *,
        job_id: str,
        kind: ArtifactKind,
        frame: pd.DataFrame,
        filename: str,
        description: str,
    ) -> ArtifactRecord:
        return self.storage.write_bytes(
            job_id=job_id,
            kind=kind,
            filename=filename,
            content_type="text/csv",
            data=frame.to_csv(index=False).encode("utf-8"),
            description=description,
        )

    def save_json(
        self,
        *,
        job_id: str,
        kind: ArtifactKind,
        payload: dict[str, Any],
        filename: str,
        description: str,
    ) -> ArtifactRecord:
        return self.storage.write_bytes(
            job_id=job_id,
            kind=kind,
            filename=filename,
            content_type="application/json",
            data=json.dumps(payload, indent=2, default=self._json_default).encode("utf-8"),
            description=description,
        )

    def save_model(
        self,
        *,
        job_id: str,
        kind: ArtifactKind,
        model: LinearModelArtifact,
        filename: str,
        description: str,
    ) -> ArtifactRecord:
        return self.save_json(
            job_id=job_id,
            kind=kind,
            payload=model.model_dump(),
            filename=filename,
            description=description,
        )

    def save_text(
        self,
        *,
        job_id: str,
        kind: ArtifactKind,
        content: str,
        filename: str,
        description: str,
    ) -> ArtifactRecord:
        return self.storage.write_bytes(
            job_id=job_id,
            kind=kind,
            filename=filename,
            content_type="text/markdown",
            data=content.encode("utf-8"),
            description=description,
        )

    def build_download_response(self, artifact: ArtifactRecord) -> ArtifactDownloadResponse:
        download_url, expires_at = self.storage.get_download_url(
            artifact,
            self.settings.download_url_ttl_minutes,
        )
        return ArtifactDownloadResponse(
            kind=artifact.kind,
            artifact_uri=artifact.artifact_uri,
            download_url=download_url,
            expires_at=datetime.fromisoformat(expires_at),
            content_type=artifact.content_type,
            filename=artifact.filename,
        )

    def find_artifact(
        self,
        job: AuditJobRecord,
        kind: ArtifactKind,
    ) -> ArtifactRecord:
        for artifact in job.artifacts:
            if artifact.kind == kind:
                return artifact
        raise NotFoundError(f"Artifact '{kind.value}' was not found for job '{job.job_id}'.")

    def resolve_local_download(self, token: str) -> tuple[bytes, str, str]:
        return self.storage.resolve_download_token(token)

    @staticmethod
    def _json_default(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError(f"Unsupported JSON type: {type(value)!r}")

