from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.domain import FairnessReport
from app.models.enums import ArtifactKind


class ArtifactDownloadResponse(BaseModel):
    kind: ArtifactKind
    artifact_uri: str
    download_url: str
    expires_at: datetime
    content_type: str
    filename: str


class FairnessReportResponse(BaseModel):
    report: FairnessReport

