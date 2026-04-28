from __future__ import annotations

from fastapi import status


class FairLensError(Exception):
    """Base application exception with an HTTP status code."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "fairlens_error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class NotFoundError(FairLensError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            code="not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ConflictError(FairLensError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            code="conflict",
            status_code=status.HTTP_409_CONFLICT,
        )


class InvalidStateError(FairLensError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            code="invalid_state",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

