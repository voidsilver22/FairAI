from __future__ import annotations

import json
from threading import Lock, Thread
from typing import Any, Callable, Protocol

from app.core.config import Settings
from app.core.exceptions import InvalidStateError

JobHandler = Callable[[dict[str, Any]], None]


class QueueAdapter(Protocol):
    backend_name: str

    def publish_job(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def subscribe_jobs(self, handler: JobHandler) -> None: ...


class LocalQueueAdapter:
    backend_name = "local"

    def __init__(self) -> None:
        self._handler: JobHandler | None = None
        self._lock = Lock()
        self._published = 0

    def publish_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self._handler is None:
            raise InvalidStateError("No local job subscriber has been registered.")

        with self._lock:
            self._published += 1
            reference = f"local-queue:{self._published}"

        thread = Thread(
            target=self._handler,
            args=(payload,),
            name=f"fairlens-job-{reference}",
            daemon=True,
        )
        thread.start()
        return {
            "backend": self.backend_name,
            "reference": reference,
            "payload_size": len(json.dumps(payload)),
        }

    def subscribe_jobs(self, handler: JobHandler) -> None:
        self._handler = handler


class PubSubQueueAdapter:
    backend_name = "pubsub"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._handler: JobHandler | None = None

    def publish_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "backend": self.backend_name,
            "reference": "pubsub-stub",
            "topic": f"projects/{self.settings.gcp_project or 'unset'}/topics/fairlens-audit-jobs",
            "payload_size": len(json.dumps(payload)),
            "implemented": False,
        }

    def subscribe_jobs(self, handler: JobHandler) -> None:
        self._handler = handler


def build_queue_adapter(settings: Settings) -> QueueAdapter:
    if settings.queue_backend == "pubsub":
        return PubSubQueueAdapter(settings)
    return LocalQueueAdapter()
