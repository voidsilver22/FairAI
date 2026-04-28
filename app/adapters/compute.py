from __future__ import annotations

from typing import Any, Protocol

from app.core.config import Settings


class ComputeAdapter(Protocol):
    backend_name: str

    def submit_audit_job(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class LocalComputeAdapter:
    backend_name = "local"

    def submit_audit_job(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "backend": self.backend_name,
            "reference": f"local-compute:{job_id}",
            "mode": "inline",
            "payload_keys": sorted(payload.keys()),
        }


class VertexAIComputeAdapter:
    backend_name = "vertex"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def submit_audit_job(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        from google.cloud import aiplatform

        aiplatform.init(
            project=self.settings.gcp_project,
            location=self.settings.vertex_location,
        )
        display_name = f"fairlens-audit-{job_id}"
        job = aiplatform.CustomContainerTrainingJob(
            display_name=display_name,
            container_uri=self.settings.bias_engine_image or "",
        )
        return {
            "backend": self.backend_name,
            "reference": display_name,
            "image": self.settings.bias_engine_image,
            "payload": payload,
        }


def build_compute_adapter(settings: Settings) -> ComputeAdapter:
    if settings.compute_backend == "vertex":
        return VertexAIComputeAdapter(settings)
    return LocalComputeAdapter()

