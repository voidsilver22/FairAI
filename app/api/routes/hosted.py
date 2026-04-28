from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_container
from app.core.security import enforce_hosted_api_key, hosted_api_key_header
from app.schemas.hosted import HostedScoreRequest, HostedScoreResponse
from app.services.runtime import ApplicationContainer

router = APIRouter()


@router.post("/hosted/score", response_model=HostedScoreResponse)
async def hosted_score(
    payload: HostedScoreRequest,
    api_key: str | None = Depends(hosted_api_key_header),
    container: ApplicationContainer = Depends(get_container),
) -> HostedScoreResponse:
    enforce_hosted_api_key(container.settings, api_key)
    return container.job_service.score_hosted_resume(payload.job_id, payload.resume_text)
