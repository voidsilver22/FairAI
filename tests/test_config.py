from __future__ import annotations

from app.core.config import Settings


def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("FAIRLENS_STORAGE_BACKEND", "local")
    monkeypatch.setenv("FAIRLENS_QUEUE_BACKEND", "pubsub")
    monkeypatch.setenv("GCP_PROJECT", "fairlens-test-project")
    settings = Settings()

    assert settings.storage_backend == "local"
    assert settings.queue_backend == "pubsub"
    assert settings.gcp_project == "fairlens-test-project"

