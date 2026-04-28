from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse
from uuid import uuid4

from app.core.config import Settings
from app.core.exceptions import InvalidStateError, NotFoundError
from app.ml.utils import utc_now
from app.models.domain import ArtifactRecord, UploadRecord
from app.models.enums import ArtifactKind, UploadStatus


class StorageAdapter(Protocol):
    backend_name: str

    def init_upload(self, filename: str, content_type: str, ttl_minutes: int) -> UploadRecord: ...

    def generate_upload_url(self, filename: str, content_type: str, ttl_minutes: int) -> UploadRecord: ...

    def generate_download_url(
        self,
        *,
        file_uri: str,
        filename: str,
        content_type: str,
        ttl_minutes: int,
    ) -> tuple[str, str]: ...

    def save_file(
        self,
        *,
        file_id: str,
        filename: str,
        content_type: str,
        data: bytes,
        namespace: str,
    ) -> str: ...

    def get_file(self, file_uri: str) -> bytes: ...

    def get_upload(self, upload_id: str) -> UploadRecord: ...

    def complete_upload(
        self,
        upload_id: str,
        *,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> UploadRecord: ...

    def artifact_exists(self, artifact_uri: str) -> bool: ...

    def read_bytes(self, artifact_uri: str) -> bytes: ...

    def write_bytes(
        self,
        *,
        job_id: str,
        kind: ArtifactKind,
        filename: str,
        content_type: str,
        data: bytes,
        description: str,
    ) -> ArtifactRecord: ...

    def get_download_url(
        self,
        artifact: ArtifactRecord,
        ttl_minutes: int,
    ) -> tuple[str, str]: ...

    def resolve_download_token(self, token: str) -> tuple[bytes, str, str]: ...


class LocalStorageAdapter:
    backend_name = "local"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root = settings.resolved_storage_root()
        self.contracts_dir = self.root / "uploads" / "contracts"
        self.contracts_dir.mkdir(parents=True, exist_ok=True)

    def generate_upload_url(self, filename: str, content_type: str, ttl_minutes: int) -> UploadRecord:
        upload_id = str(uuid4())
        safe_filename = Path(filename).name
        artifact_uri = self._build_local_uri(
            namespace="uploads/blobs",
            file_id=upload_id,
            filename=safe_filename,
        )
        record = UploadRecord(
            upload_id=upload_id,
            filename=safe_filename,
            content_type=content_type,
            artifact_uri=artifact_uri,
            upload_url=f"/local-upload/{upload_id}",
            storage_mode=self.backend_name,
            headers={},
            created_at=utc_now(),
            expires_at=utc_now() + timedelta(minutes=ttl_minutes),
            status=UploadStatus.INITIATED,
        )
        self._write_contract(record)
        return record

    def generate_download_url(
        self,
        *,
        file_uri: str,
        filename: str,
        content_type: str,
        ttl_minutes: int,
    ) -> tuple[str, str]:
        expires_at = utc_now() + timedelta(minutes=ttl_minutes)
        payload = {
            "artifact_uri": file_uri,
            "content_type": content_type,
            "filename": filename,
            "expires_at": expires_at.isoformat(),
        }
        token = self._sign_payload(payload)
        return (f"{self.settings.api_v1_prefix}/downloads/{token}", expires_at.isoformat())

    def save_file(
        self,
        *,
        file_id: str,
        filename: str,
        content_type: str,
        data: bytes,
        namespace: str,
    ) -> str:
        del content_type
        safe_filename = Path(filename).name
        relative_path = Path(namespace) / f"{file_id}_{safe_filename}"
        resolved_path = self.root / relative_path
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_path.write_bytes(data)
        return f"local://{relative_path.as_posix()}"

    def get_file(self, file_uri: str) -> bytes:
        path = self._resolve_local_uri(file_uri)
        if not path.exists():
            raise NotFoundError(f"Artifact '{file_uri}' was not found.")
        return path.read_bytes()

    def get_upload(self, upload_id: str) -> UploadRecord:
        path = self.contracts_dir / f"{upload_id}.json"
        if not path.exists():
            raise NotFoundError(f"Upload contract '{upload_id}' was not found.")
        return UploadRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def complete_upload(
        self,
        upload_id: str,
        *,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> UploadRecord:
        record = self.get_upload(upload_id)
        if record.status == UploadStatus.COMPLETED:
            raise InvalidStateError(f"Upload '{upload_id}' is already completed.")
        if utc_now() > record.expires_at:
            raise InvalidStateError(f"Upload '{upload_id}' has expired.")

        artifact_uri = self.save_file(
            file_id=upload_id,
            filename=filename,
            content_type=content_type,
            data=data,
            namespace="uploads/blobs",
        )
        updated = record.model_copy(
            update={
                "filename": Path(filename).name,
                "content_type": content_type,
                "artifact_uri": artifact_uri,
                "status": UploadStatus.COMPLETED,
            }
        )
        self._write_contract(updated)
        return updated

    def artifact_exists(self, artifact_uri: str) -> bool:
        return self._resolve_local_uri(artifact_uri).exists()

    def read_bytes(self, artifact_uri: str) -> bytes:
        return self.get_file(artifact_uri)

    def write_bytes(
        self,
        *,
        job_id: str,
        kind: ArtifactKind,
        filename: str,
        content_type: str,
        data: bytes,
        description: str,
    ) -> ArtifactRecord:
        artifact_uri = self.save_file(
            file_id=f"{job_id}-{kind.value}",
            filename=filename,
            content_type=content_type,
            data=data,
            namespace=f"artifacts/jobs/{job_id}",
        )
        return ArtifactRecord(
            kind=kind,
            artifact_uri=artifact_uri,
            filename=Path(filename).name,
            content_type=content_type,
            description=description,
            created_at=utc_now(),
            size_bytes=len(data),
        )

    def get_download_url(
        self,
        artifact: ArtifactRecord,
        ttl_minutes: int,
    ) -> tuple[str, str]:
        return self.generate_download_url(
            file_uri=artifact.artifact_uri,
            filename=artifact.filename,
            content_type=artifact.content_type,
            ttl_minutes=ttl_minutes,
        )

    def resolve_download_token(self, token: str) -> tuple[bytes, str, str]:
        payload = self._verify_payload(token)
        return (
            self.get_file(str(payload["artifact_uri"])),
            str(payload["content_type"]),
            str(payload["filename"]),
        )

    def init_upload(self, filename: str, content_type: str, ttl_minutes: int) -> UploadRecord:
        return self.generate_upload_url(filename, content_type, ttl_minutes)

    def _write_contract(self, record: UploadRecord) -> None:
        contract_path = self.contracts_dir / f"{record.upload_id}.json"
        contract_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    def _build_local_uri(self, *, namespace: str, file_id: str, filename: str) -> str:
        safe_filename = Path(filename).name
        relative_path = Path(namespace) / f"{file_id}_{safe_filename}"
        return f"local://{relative_path.as_posix()}"

    def _resolve_local_uri(self, artifact_uri: str) -> Path:
        parsed = urlparse(artifact_uri)
        if parsed.scheme != "local":
            raise InvalidStateError(f"Unsupported local artifact URI: {artifact_uri}")
        relative = parsed.netloc + parsed.path
        return self.root / relative.lstrip("/")

    def _sign_payload(self, payload: dict[str, str]) -> str:
        raw_payload = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = hmac.new(
            self.settings.signed_url_secret.encode("utf-8"),
            raw_payload,
            hashlib.sha256,
        ).hexdigest()
        token_payload = base64.urlsafe_b64encode(raw_payload).decode("utf-8").rstrip("=")
        return f"{token_payload}.{signature}"

    def _verify_payload(self, token: str) -> dict[str, str]:
        try:
            payload_encoded, signature = token.rsplit(".", 1)
        except ValueError as error:
            raise InvalidStateError("Malformed download token.") from error

        padded = payload_encoded + "=" * (-len(payload_encoded) % 4)
        raw_payload = base64.urlsafe_b64decode(padded.encode("utf-8"))
        expected = hmac.new(
            self.settings.signed_url_secret.encode("utf-8"),
            raw_payload,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise InvalidStateError("Invalid download token signature.")

        payload = json.loads(raw_payload.decode("utf-8"))
        expires_at = datetime.fromisoformat(payload["expires_at"])
        if utc_now() > expires_at:
            raise InvalidStateError("Download token has expired.")
        return payload


class GCSStorageAdapter:
    backend_name = "gcs"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate_upload_url(self, filename: str, content_type: str, ttl_minutes: int) -> UploadRecord:
        upload_id = str(uuid4())
        safe_filename = Path(filename).name
        blob_name = f"uploads/{upload_id}/{safe_filename}"
        artifact_uri = f"gs://{self.settings.uploads_bucket}/{blob_name}"
        upload_url = self.generate_signed_upload_url(
            self.settings.uploads_bucket,
            blob_name,
            content_type=content_type,
            ttl_minutes=ttl_minutes,
        )
        return UploadRecord(
            upload_id=upload_id,
            filename=safe_filename,
            content_type=content_type,
            artifact_uri=artifact_uri,
            upload_url=upload_url,
            storage_mode=self.backend_name,
            headers={"Content-Type": content_type},
            created_at=utc_now(),
            expires_at=utc_now() + timedelta(minutes=ttl_minutes),
            status=UploadStatus.INITIATED,
        )

    def generate_download_url(
        self,
        *,
        file_uri: str,
        filename: str,
        content_type: str,
        ttl_minutes: int,
    ) -> tuple[str, str]:
        del filename
        del content_type
        bucket_name, blob_name = _parse_gcs_uri(file_uri)
        expires_at = utc_now() + timedelta(minutes=ttl_minutes)
        return (
            self.generate_signed_download_url(
                bucket_name,
                blob_name,
                ttl_minutes=ttl_minutes,
            ),
            expires_at.isoformat(),
        )

    def save_file(
        self,
        *,
        file_id: str,
        filename: str,
        content_type: str,
        data: bytes,
        namespace: str,
    ) -> str:
        del content_type
        del data
        safe_filename = Path(filename).name
        blob_name = f"{namespace.strip('/')}/{file_id}_{safe_filename}"
        return f"gs://{self.settings.results_bucket}/{blob_name}"

    def get_file(self, file_uri: str) -> bytes:
        raise InvalidStateError(
            f"Direct file reads are not implemented for '{self.backend_name}' mode yet: {file_uri}"
        )

    def get_upload(self, upload_id: str) -> UploadRecord:
        raise InvalidStateError(
            f"GCS upload contracts are not persisted by the local API stub: {upload_id}"
        )

    def complete_upload(
        self,
        upload_id: str,
        *,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> UploadRecord:
        del upload_id
        del filename
        del content_type
        del data
        raise InvalidStateError("Direct upload completion is not supported for the GCS backend.")

    def artifact_exists(self, artifact_uri: str) -> bool:
        return artifact_uri.startswith("gs://")

    def read_bytes(self, artifact_uri: str) -> bytes:
        return self.get_file(artifact_uri)

    def write_bytes(
        self,
        *,
        job_id: str,
        kind: ArtifactKind,
        filename: str,
        content_type: str,
        data: bytes,
        description: str,
    ) -> ArtifactRecord:
        artifact_uri = self.save_file(
            file_id=f"{job_id}-{kind.value}",
            filename=filename,
            content_type=content_type,
            data=data,
            namespace=f"artifacts/jobs/{job_id}",
        )
        return ArtifactRecord(
            kind=kind,
            artifact_uri=artifact_uri,
            filename=Path(filename).name,
            content_type=content_type,
            description=description,
            created_at=utc_now(),
            size_bytes=len(data),
        )

    def get_download_url(
        self,
        artifact: ArtifactRecord,
        ttl_minutes: int,
    ) -> tuple[str, str]:
        return self.generate_download_url(
            file_uri=artifact.artifact_uri,
            filename=artifact.filename,
            content_type=artifact.content_type,
            ttl_minutes=ttl_minutes,
        )

    def resolve_download_token(self, token: str) -> tuple[bytes, str, str]:
        del token
        raise InvalidStateError("Download tokens are handled directly by GCS in cloud mode.")

    def init_upload(self, filename: str, content_type: str, ttl_minutes: int) -> UploadRecord:
        return self.generate_upload_url(filename, content_type, ttl_minutes)

    def generate_signed_upload_url(
        self,
        bucket: str,
        filename: str,
        *,
        content_type: str,
        ttl_minutes: int,
    ) -> str:
        return (
            f"https://gcs.stub/{bucket}/{filename}"
            f"?method=PUT&content_type={content_type}&ttl_minutes={ttl_minutes}"
        )

    def generate_signed_download_url(
        self,
        bucket: str,
        filename: str,
        *,
        ttl_minutes: int,
    ) -> str:
        return f"https://gcs.stub/{bucket}/{filename}?method=GET&ttl_minutes={ttl_minutes}"


def build_storage_adapter(settings: Settings) -> StorageAdapter:
    if settings.storage_backend == "gcs":
        return GCSStorageAdapter(settings)
    return LocalStorageAdapter(settings)


def _parse_gcs_uri(uri: str) -> tuple[str, str]:
    parsed = urlparse(uri)
    if parsed.scheme != "gs":
        raise InvalidStateError(f"Invalid GCS URI: {uri}")
    bucket_name = parsed.netloc
    blob_name = parsed.path.lstrip("/")
    return bucket_name, blob_name
