"""
API Middleware
"""
from .auth import verify_api_key

__all__ = ["verify_api_key"]
