"""
SDK error types for ainative-agent.

Built by AINative Dev Team.
"""
from __future__ import annotations


class AINativeError(Exception):
    """Base error for all ainative-agent SDK errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"status_code={self.status_code!r})"
        )


class AuthError(AINativeError):
    """Raised when authentication fails (401 / 403)."""


class NotFoundError(AINativeError):
    """Raised when a requested resource is not found (404)."""


class ValidationError(AINativeError):
    """Raised when request data fails server-side validation (422)."""


class RateLimitError(AINativeError):
    """Raised when the API rate limit is exceeded (429)."""


class ServerError(AINativeError):
    """Raised on 5xx server-side errors."""


class DimensionError(AINativeError):
    """Raised when vector embedding dimension is not supported."""

    SUPPORTED_DIMENSIONS: tuple[int, ...] = (384, 768, 1024, 1536)

    def __init__(self, actual: int) -> None:
        super().__init__(
            f"Unsupported embedding dimension {actual}. "
            f"Supported: {self.SUPPORTED_DIMENSIONS}"
        )
        self.actual = actual
