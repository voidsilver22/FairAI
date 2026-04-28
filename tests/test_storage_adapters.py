from __future__ import annotations

from app.adapters.storage import GCSStorageAdapter, LocalStorageAdapter
from app.core.config import Settings
from app.models.enums import ArtifactKind


def test_local_storage_round_trip(tmp_path):
    settings = Settings(
        storage_backend="local",
        local_storage_root=tmp_path,
        signed_url_secret="test-secret",
    )
    adapter = LocalStorageAdapter(settings)
    upload = adapter.generate_upload_url("dataset.csv", "text/csv", ttl_minutes=5)

    assert upload.upload_url.startswith("/local-upload/")
    assert upload.storage_mode == "local"

    adapter.complete_upload(
        upload.upload_id,
        filename="dataset.csv",
        content_type="text/csv",
        data=b"col\nvalue\n",
    )
    artifact = adapter.write_bytes(
        job_id="job-1",
        kind=ArtifactKind.REPORT_JSON,
        filename="report.json",
        content_type="application/json",
        data=b"{}",
        description="report",
    )
    download_url, _ = adapter.generate_download_url(
        file_uri=artifact.artifact_uri,
        filename=artifact.filename,
        content_type=artifact.content_type,
        ttl_minutes=5,
    )
    token = download_url.rsplit("/", 1)[-1]
    payload, content_type, filename = adapter.resolve_download_token(token)

    assert adapter.artifact_exists(upload.artifact_uri)
    assert adapter.get_file(upload.artifact_uri) == b"col\nvalue\n"
    assert payload == b"{}"
    assert content_type == "application/json"
    assert filename == "report.json"


def test_gcs_storage_returns_stubbed_signed_urls():
    settings = Settings(
        storage_backend="gcs",
        gcp_project="fairlens-test",
        uploads_bucket="fairlens-uploads",
        results_bucket="fairlens-results",
    )
    adapter = GCSStorageAdapter(settings)

    upload = adapter.generate_upload_url("dataset.csv", "text/csv", ttl_minutes=5)
    artifact = adapter.write_bytes(
        job_id="job-123",
        kind=ArtifactKind.REPORT_JSON,
        filename="report.json",
        content_type="application/json",
        data=b"{}",
        description="report",
    )
    download_url, _ = adapter.get_download_url(artifact, ttl_minutes=5)

    assert upload.storage_mode == "gcs"
    assert upload.upload_url.startswith("https://gcs.stub/")
    assert artifact.artifact_uri.startswith("gs://fairlens-results/")
    assert download_url.startswith("https://gcs.stub/")
