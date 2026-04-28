from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import UploadStatus


class UploadInitRequest(BaseModel):
    filename: str
    content_type: str = "text/csv"


class UploadInitResponse(BaseModel):
    file_id: str
    file_uri: str
    upload_url: str
    storage_mode: str
    headers: dict[str, str]
    expires_at: datetime
    status: UploadStatus


class UploadCompleteResponse(BaseModel):
    file_id: str
    file_uri: str
    storage_mode: str
    status: UploadStatus
