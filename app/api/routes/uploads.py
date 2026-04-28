from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from app.api.dependencies import get_container
from app.core.exceptions import InvalidStateError
from app.schemas.uploads import (
    UploadCompleteResponse,
    UploadInitRequest,
    UploadInitResponse,
)
from app.services.runtime import ApplicationContainer

router = APIRouter()
local_upload_router = APIRouter()


@router.post("/uploads/init", response_model=UploadInitResponse)
async def init_upload(
    payload: UploadInitRequest,
    container: ApplicationContainer = Depends(get_container),
) -> UploadInitResponse:
    record = container.upload_service.init_upload(payload.filename, payload.content_type)
    return UploadInitResponse(
        file_id=record.upload_id,
        file_uri=record.artifact_uri,
        upload_url=record.upload_url,
        storage_mode=record.storage_mode,
        headers=record.headers,
        expires_at=record.expires_at,
        status=record.status,
    )


@router.post("/uploads/{upload_id}/content", response_model=UploadCompleteResponse, include_in_schema=False)
@local_upload_router.post("/local-upload/{upload_id}", response_model=UploadCompleteResponse)
async def upload_content(
    upload_id: str,
    file: UploadFile = File(...),
    container: ApplicationContainer = Depends(get_container),
) -> UploadCompleteResponse:
    if container.storage.backend_name != "local":
        raise InvalidStateError("Direct upload completion is only available in local mode.")

    data = await file.read()
    record = container.upload_service.complete_upload(
        upload_id,
        filename=file.filename or "upload.csv",
        content_type=file.content_type or "application/octet-stream",
        data=data,
    )
    return UploadCompleteResponse(
        file_id=record.upload_id,
        file_uri=record.artifact_uri,
        storage_mode=record.storage_mode,
        status=record.status,
    )


@router.get("/downloads/{token}")
async def download_artifact(
    token: str,
    container: ApplicationContainer = Depends(get_container),
) -> Response:
    payload, content_type, filename = container.artifact_service.resolve_local_download(token)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=payload, media_type=content_type, headers=headers)
