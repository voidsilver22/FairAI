from __future__ import annotations

from fastapi import Header

from app.core.config import Settings
from app.core.exceptions import FairLensError


def enforce_hosted_api_key(
    settings: Settings,
    api_key: str | None,
) -> None:
    """Validate hosted scoring access when an API key is configured."""

    if not settings.hosted_api_key:
        return

    if api_key != settings.hosted_api_key:
        raise FairLensError(
            "Invalid hosted API key.",
            code="invalid_api_key",
            status_code=401,
        )


async def hosted_api_key_header(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> str | None:
    return x_api_key

