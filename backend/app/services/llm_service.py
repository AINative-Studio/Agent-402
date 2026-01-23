"""
LLM Service Abstraction Layer.
Provides a unified interface for LLM providers.

Issue #115: Gemini AI Integration

This module implements:
- LLMService abstract base class
- GeminiLLMAdapter for Gemini integration
- Factory function for service creation

Future adapters:
- OpenAILLMAdapter
- AnthropicLLMAdapter

Per PRD Section 12 (AI Integration):
- Abstraction layer enables provider switching
- Standardized request/response format
- Consistent error handling across providers
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging

from app.core.errors import APIError

logger = logging.getLogger(__name__)


class LLMServiceError(APIError):
    """
    Base error for LLM service failures.

    Returns:
        - HTTP 502 (Bad Gateway)
        - error_code: LLM_SERVICE_ERROR
        - detail: Message about the failure
    """

    def __init__(self, detail: str = "LLM service error"):
        super().__init__(
            status_code=502,
            error_code="LLM_SERVICE_ERROR",
            detail=detail or "LLM service error"
        )


class LLMService(ABC):
    """
    Abstract base class for LLM service implementations.

    This interface defines the contract that all LLM adapters must implement.
    Enables switching between providers (Gemini, OpenAI, Anthropic) without
    changing application code.
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        timeout_seconds: float = 30,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate text from a prompt.

        Args:
            prompt: The prompt to generate from
            model: Model to use (provider-specific)
            system_instruction: Optional system instruction
            timeout_seconds: Request timeout
            max_retries: Maximum retries on failure

        Returns:
            Dict with:
            - text: Generated text
            - model: Model used
            - latency_ms: Response time in milliseconds
        """
        pass

    @abstractmethod
    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        model: Optional[str] = None,
        timeout_seconds: float = 30,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate with function calling support.

        Args:
            prompt: The prompt to generate from
            tools: List of tool definitions
            model: Model to use
            timeout_seconds: Request timeout
            max_retries: Maximum retries

        Returns:
            Dict with:
            - function_call: If a function was called (name and args)
            - text: If no function matched
            - model: Model used
            - latency_ms: Response time
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_schema: Dict[str, Any],
        model: Optional[str] = None,
        timeout_seconds: float = 30,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate structured output matching a schema.

        Args:
            prompt: The prompt to generate from
            response_schema: JSON schema for expected response
            model: Model to use
            timeout_seconds: Request timeout
            max_retries: Maximum retries

        Returns:
            Dict with:
            - parsed: Parsed JSON response
            - raw: Raw text response
            - model: Model used
            - latency_ms: Response time
        """
        pass


class GeminiLLMAdapter(LLMService):
    """
    Gemini adapter implementing LLMService interface.

    Wraps GeminiService to provide standardized interface
    compatible with the LLMService contract.
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "gemini-pro"
    ):
        """
        Initialize Gemini adapter.

        Args:
            api_key: Google Gemini API key
            default_model: Default model to use
        """
        from app.services.gemini_service import GeminiService
        self._service = GeminiService(
            api_key=api_key,
            default_model=default_model
        )

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        timeout_seconds: float = 30,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate text using Gemini.

        Delegates to GeminiService.generate().
        """
        return await self._service.generate(
            prompt=prompt,
            model=model,
            system_instruction=system_instruction,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries
        )

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        model: Optional[str] = None,
        timeout_seconds: float = 30,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate with function calling using Gemini.

        Delegates to GeminiService.generate_with_tools().
        """
        return await self._service.generate_with_tools(
            prompt=prompt,
            tools=tools,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries
        )

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Dict[str, Any],
        model: Optional[str] = None,
        timeout_seconds: float = 30,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate structured output using Gemini.

        Delegates to GeminiService.generate_structured().
        """
        return await self._service.generate_structured(
            prompt=prompt,
            response_schema=response_schema,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries
        )


# Future adapters can be added here
# class OpenAILLMAdapter(LLMService):
#     """OpenAI adapter implementing LLMService interface."""
#     pass
#
# class AnthropicLLMAdapter(LLMService):
#     """Anthropic adapter implementing LLMService interface."""
#     pass


# Factory function
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """
    Get or create the LLM service.

    Returns LLMService implementation based on settings.
    Currently returns GeminiLLMAdapter.

    Returns:
        LLMService instance
    """
    global _llm_service
    if _llm_service is None:
        from app.core.config import settings

        provider = getattr(settings, 'llm_provider', 'gemini')

        if provider == "gemini":
            _llm_service = GeminiLLMAdapter(
                api_key=settings.gemini_api_key,
                default_model=settings.gemini_pro_model
            )
        else:
            # Default to Gemini
            _llm_service = GeminiLLMAdapter(
                api_key=settings.gemini_api_key,
                default_model=settings.gemini_pro_model
            )

    return _llm_service


def reset_llm_service() -> None:
    """Reset the LLM service singleton (for testing)."""
    global _llm_service
    _llm_service = None
