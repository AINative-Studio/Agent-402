"""
Custom exception classes for ZeroDB API.

Per DX Contract §7 (Error Semantics):
- All errors return { detail, error_code }
- Error codes are stable and documented
- Validation errors use HTTP 422
"""
from typing import Optional, Dict, Any
from fastapi import status


class ZeroDBException(Exception):
    """
    Base exception class for all ZeroDB custom exceptions.

    All custom exceptions should inherit from this class to ensure
    consistent error handling and formatting.
    """

    def __init__(
        self,
        detail: str,
        error_code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        headers: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize ZeroDB exception.

        Args:
            detail: Human-readable error message
            error_code: Machine-readable error code
            status_code: HTTP status code (default: 500)
            headers: Optional HTTP headers
        """
        super().__init__(detail)
        self.detail = detail
        self.error_code = error_code
        self.status_code = status_code
        self.headers = headers or {}
