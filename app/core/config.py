from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="FAIRLENS_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "FairLens ATS Pipeline"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    storage_backend: Literal["local", "gcs"] = Field(
        default="local",
        validation_alias=AliasChoices("FAIRLENS_STORAGE_BACKEND", "STORAGE_MODE"),
    )
    queue_backend: Literal["local", "pubsub"] = Field(
        default="local",
        validation_alias=AliasChoices("FAIRLENS_QUEUE_BACKEND", "QUEUE_MODE"),
    )
    compute_backend: Literal["local", "vertex"] = Field(
        default="local",
        validation_alias=AliasChoices("FAIRLENS_COMPUTE_BACKEND", "COMPUTE_MODE"),
    )

    local_storage_root: Path = Path(".fairlens-data")
    model_training_workspace: Path = Path("Model Training")
    upload_url_ttl_minutes: int = 30
    download_url_ttl_minutes: int = 30
    signed_url_secret: str = "local-fairlens-secret"
    execute_inline_jobs: bool = False

    pipeline_random_state: int = 42
    default_fairness_weight: float = 0.35
    max_counterfactual_samples: int = 128
    hosted_api_key: str | None = None

    gcp_project: str | None = Field(
        default=None,
        validation_alias=AliasChoices("FAIRLENS_GCP_PROJECT", "GCP_PROJECT"),
    )
    google_application_credentials: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_APPLICATION_CREDENTIALS"),
    )
    uploads_bucket: str = "fairlens-uploads"
    results_bucket: str = "fairlens-results"
    archive_bucket: str = "fairlens-archive"
    bq_dataset: str = "fairlens_audit"
    vertex_location: str = "us-central1"
    bias_engine_image: str | None = None
    dlp_enabled: bool = False

    def resolved_storage_root(self) -> Path:
        return self.local_storage_root.resolve()

    def resolved_model_training_workspace(self) -> Path:
        return self.model_training_workspace.resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
