from __future__ import annotations

from app.services.runtime import ApplicationContainer, get_application_container


async def get_container() -> ApplicationContainer:
    return get_application_container()
