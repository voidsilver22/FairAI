from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class JobExecutionMessage(BaseModel):
    job_id: str
    file_uri: str
    config: dict[str, object]
    requested_at: datetime
