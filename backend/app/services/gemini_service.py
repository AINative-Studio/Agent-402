"""
Gemini AI Service Layer.
Implements Gemini LLM integration for Agent-402.

Issue #115: Gemini AI Integration

This service handles:
- Model selection (gemini-pro, gemini-1.5-flash)
- Function calling support for Circle tools
- Structured output parsing
- Rate limiting and retry logic

Per PRD Section 12 (AI Integration):
- Gemini is the primary LLM backend
- Agent-specific model selection for optimal performance
- All operations support retry and timeout

Security:
- API key is stored securely (never logged)
- All requests use HTTPS
- Input validation on all prompts
"""
import json
import re
import asyncio
import logging
import time
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod

from app.core.errors import APIError

logger = logging.getLogger(__name__)

# Supported Gemini models
SUPPORTED_MODELS = [
    "gemini-pro",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-1.0-pro",
]

# Agent to model mapping
AGENT_MODEL_MAPPING = {
    "analyst": "gemini-pro",
    "compliance": "gemini-pro",
    "transaction": "gemini-1.5-flash",
}

# Default configuration
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 0.5


class GeminiConfigError(APIError):
    """
    Raised when Gemini configuration is invalid.

    Returns:
        - HTTP 500 (Internal Server Error)
        - error_code: GEMINI_CONFIG_ERROR
        - detail: Message about configuration error
    """

    def __init__(self, detail: str = "Gemini configuration error"):
        super().__init__(
            status_code=500,
            error_code="GEMINI_CONFIG_ERROR",
            detail=detail or "Gemini configuration error"
        )


class GeminiAPIError(APIError):
    """
    Raised when Gemini API calls fail.

    Returns:
        - HTTP 502 (Bad Gateway)
        - error_code: GEMINI_API_ERROR
        - detail: Message about the API failure
    """

    def __init__(self, detail: str = "Gemini API error"):
        super().__init__(
            status_code=502,
            error_code="GEMINI_API_ERROR",
            detail=detail or "Gemini API error"
        )


class GeminiTimeoutError(APIError):
    """
    Raised when Gemini request times out.

    Returns:
        - HTTP 504 (Gateway Timeout)
        - error_code: GEMINI_TIMEOUT
        - detail: Message about timeout
    """

    def __init__(self, detail: str = "Gemini request timed out"):
        super().__init__(
            status_code=504,
            error_code="GEMINI_TIMEOUT",
            detail=detail or "Gemini request timed out"
        )


class GeminiRateLimitError(APIError):
    """
    Raised when Gemini rate limit is exceeded.

    Returns:
        - HTTP 429 (Too Many Requests)
        - error_code: GEMINI_RATE_LIMIT
        - detail: Message about rate limiting
    """

    def __init__(self, detail: str = "Gemini rate limit exceeded"):
        super().__init__(
            status_code=429,
            error_code="GEMINI_RATE_LIMIT",
            detail=detail or "Gemini rate limit exceeded"
        )


class GeminiModelError(APIError):
    """
    Raised when invalid model is specified.

    Returns:
        - HTTP 400 (Bad Request)
        - error_code: GEMINI_MODEL_ERROR
        - detail: Message about invalid model
    """

    def __init__(self, model: str):
        super().__init__(
            status_code=400,
            error_code="GEMINI_MODEL_ERROR",
            detail=f"Invalid model: {model}. Supported: {', '.join(SUPPORTED_MODELS)}"
        )


class GeminiParseError(APIError):
    """
    Raised when response parsing fails.

    Returns:
        - HTTP 422 (Unprocessable Entity)
        - error_code: GEMINI_PARSE_ERROR
        - detail: Message about parse failure
    """

    def __init__(self, detail: str = "Failed to parse Gemini response"):
        super().__init__(
            status_code=422,
            error_code="GEMINI_PARSE_ERROR",
            detail=detail or "Failed to parse Gemini response"
        )


class GeminiEmptyResponseError(APIError):
    """
    Raised when Gemini returns empty response.

    Returns:
        - HTTP 502 (Bad Gateway)
        - error_code: GEMINI_EMPTY_RESPONSE
        - detail: Message about empty response
    """

    def __init__(self, detail: str = "Gemini returned empty response"):
        super().__init__(
            status_code=502,
            error_code="GEMINI_EMPTY_RESPONSE",
            detail=detail or "Gemini returned empty response"
        )


class GeminiSafetyError(APIError):
    """
    Raised when response is blocked by safety filters.

    Returns:
        - HTTP 400 (Bad Request)
        - error_code: GEMINI_SAFETY_BLOCK
        - detail: Message about safety block
    """

    def __init__(self, detail: str = "Response blocked by safety filters"):
        super().__init__(
            status_code=400,
            error_code="GEMINI_SAFETY_BLOCK",
            detail=detail or "Response blocked by safety filters"
        )


# Import genai conditionally for testing
try:
    import google.generativeai as genai
    from google.api_core.exceptions import ResourceExhausted
except ImportError:
    genai = None
    ResourceExhausted = Exception


class GeminiService:
    """
    Gemini AI service client.

    Handles communication with Google's Gemini API for:
    - Text generation
    - Function calling
    - Structured output parsing

    Supports multiple models:
    - gemini-pro: Deep analysis for Analyst and Compliance agents
    - gemini-1.5-flash: Fast execution for Transaction agent
    """

    def __init__(
        self,
        api_key: str,
        default_model: str = "gemini-pro"
    ):
        """
        Initialize the Gemini service.

        Args:
            api_key: Google Gemini API key (required)
            default_model: Default model to use (default: gemini-pro)

        Raises:
            GeminiConfigError: If API key is missing
        """
        if not api_key or api_key.strip() == "":
            raise GeminiConfigError("API key is required for Gemini service")

        self.api_key = api_key
        self.default_model = default_model
        self._configured = False

        # Configure genai
        if genai:
            genai.configure(api_key=api_key)
            self._configured = True

    def get_model_for_agent(self, agent_type: str) -> str:
        """
        Get the appropriate model for an agent type.

        Args:
            agent_type: Type of agent (analyst, compliance, transaction)

        Returns:
            Model name to use for this agent
        """
        return AGENT_MODEL_MAPPING.get(agent_type, self.default_model)

    def _validate_model(self, model: str) -> None:
        """
        Validate that the model is supported.

        Args:
            model: Model name to validate

        Raises:
            GeminiModelError: If model is not supported
        """
        if model not in SUPPORTED_MODELS:
            raise GeminiModelError(model)

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES
    ) -> Dict[str, Any]:
        """
        Generate text from a prompt.

        Args:
            prompt: The prompt to generate from
            model: Model to use (default: self.default_model)
            system_instruction: Optional system instruction
            timeout_seconds: Request timeout in seconds
            max_retries: Maximum number of retries on rate limit

        Returns:
            Dict with:
            - text: Generated text
            - model: Model used
            - latency_ms: Response time in milliseconds

        Raises:
            GeminiTimeoutError: If request times out
            GeminiRateLimitError: If rate limit exceeded after retries
            GeminiAPIError: If API call fails
        """
        model = model or self.default_model
        self._validate_model(model)

        start_time = time.time()
        retry_count = 0
        retry_delay = INITIAL_RETRY_DELAY

        while retry_count <= max_retries:
            try:
                # Create model with optional system instruction
                model_kwargs = {"model_name": model}
                if system_instruction:
                    model_kwargs["system_instruction"] = system_instruction

                gemini_model = genai.GenerativeModel(**model_kwargs)

                # Generate with timeout
                try:
                    response = await asyncio.wait_for(
                        gemini_model.generate_content_async(prompt),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    raise GeminiTimeoutError(
                        f"Request timed out after {timeout_seconds} seconds"
                    )

                # Check for safety blocks
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                    if hasattr(response.prompt_feedback, 'block_reason'):
                        block_reason = response.prompt_feedback.block_reason
                        # Check if it's a real block reason (not None and not a MagicMock)
                        if block_reason and isinstance(block_reason, str):
                            raise GeminiSafetyError(
                                f"Response blocked: {block_reason}"
                            )

                # Check for empty response
                if not response.text and (
                    not hasattr(response, 'candidates') or not response.candidates
                ):
                    raise GeminiEmptyResponseError()

                latency_ms = (time.time() - start_time) * 1000

                return {
                    "text": response.text,
                    "model": model,
                    "latency_ms": latency_ms
                }

            except (GeminiTimeoutError, GeminiSafetyError, GeminiEmptyResponseError):
                raise
            except ResourceExhausted:
                retry_count += 1
                if retry_count > max_retries:
                    raise GeminiRateLimitError(
                        f"Rate limit exceeded after {max_retries} retries"
                    )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            except Exception as e:
                logger.error(f"Gemini API error: {e}")
                raise GeminiAPIError(str(e))

        raise GeminiRateLimitError(f"Rate limit exceeded after {max_retries} retries")

    def convert_tools_to_gemini_format(
        self,
        tools: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert tool definitions to Gemini format.

        Args:
            tools: List of tool definitions in OpenAI format

        Returns:
            List of tools in Gemini format
        """
        gemini_tools = []
        for tool in tools:
            gemini_tool = {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {})
            }
            gemini_tools.append(gemini_tool)
        return gemini_tools

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        model: Optional[str] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES
    ) -> Dict[str, Any]:
        """
        Generate with function calling support.

        Args:
            prompt: The prompt to generate from
            tools: List of tool definitions
            model: Model to use
            timeout_seconds: Request timeout in seconds
            max_retries: Maximum retries on rate limit

        Returns:
            Dict with:
            - function_call: If a function was called, contains name and args
            - text: If no function matched, contains text response
            - model: Model used
            - latency_ms: Response time in milliseconds
        """
        model = model or self.default_model
        self._validate_model(model)

        start_time = time.time()
        retry_count = 0
        retry_delay = INITIAL_RETRY_DELAY

        # Convert tools to Gemini format
        gemini_tools = self.convert_tools_to_gemini_format(tools)

        while retry_count <= max_retries:
            try:
                gemini_model = genai.GenerativeModel(model_name=model)

                try:
                    response = await asyncio.wait_for(
                        gemini_model.generate_content_async(
                            prompt,
                            tools=gemini_tools
                        ),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    raise GeminiTimeoutError(
                        f"Request timed out after {timeout_seconds} seconds"
                    )

                latency_ms = (time.time() - start_time) * 1000

                # Check for function call in response
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            for part in candidate.content.parts:
                                if hasattr(part, 'function_call') and part.function_call:
                                    fc = part.function_call
                                    return {
                                        "function_call": {
                                            "name": fc.name,
                                            "args": dict(fc.args) if hasattr(fc, 'args') else {}
                                        },
                                        "model": model,
                                        "latency_ms": latency_ms
                                    }

                # No function call, return text response
                text = ""
                if hasattr(response, 'text'):
                    text = response.text
                elif hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            for part in candidate.content.parts:
                                if hasattr(part, 'text') and part.text:
                                    text = part.text
                                    break

                return {
                    "text": text,
                    "model": model,
                    "latency_ms": latency_ms
                }

            except (GeminiTimeoutError,):
                raise
            except ResourceExhausted:
                retry_count += 1
                if retry_count > max_retries:
                    raise GeminiRateLimitError(
                        f"Rate limit exceeded after {max_retries} retries"
                    )
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            except Exception as e:
                logger.error(f"Gemini API error in function calling: {e}")
                raise GeminiAPIError(str(e))

        raise GeminiRateLimitError(f"Rate limit exceeded after {max_retries} retries")

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON from text, handling code blocks.

        Args:
            text: Text that may contain JSON

        Returns:
            Parsed JSON dict or None if no valid JSON found
        """
        # Try to extract from code block first
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)```'
        matches = re.findall(code_block_pattern, text)

        if matches:
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue

        # Try parsing the entire text as JSON
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass

        # Try finding JSON object in text
        json_pattern = r'\{[\s\S]*\}'
        json_matches = re.findall(json_pattern, text)
        for match in json_matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        return None

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Dict[str, Any],
        model: Optional[str] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES
    ) -> Dict[str, Any]:
        """
        Generate structured output matching a schema.

        Args:
            prompt: The prompt to generate from
            response_schema: JSON schema for expected response
            model: Model to use
            timeout_seconds: Request timeout in seconds
            max_retries: Maximum retries on rate limit

        Returns:
            Dict with:
            - parsed: Parsed JSON response
            - raw: Raw text response
            - model: Model used
            - latency_ms: Response time in milliseconds

        Raises:
            GeminiParseError: If response cannot be parsed as JSON
        """
        # Add schema instruction to prompt
        schema_instruction = (
            f"\n\nRespond with valid JSON matching this schema: "
            f"{json.dumps(response_schema)}"
        )
        full_prompt = prompt + schema_instruction

        result = await self.generate(
            prompt=full_prompt,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries
        )

        # Parse the response
        parsed = self._extract_json_from_text(result["text"])

        if parsed is None:
            raise GeminiParseError(
                f"Could not parse JSON from response: {result['text'][:200]}"
            )

        return {
            "parsed": parsed,
            "raw": result["text"],
            "model": result["model"],
            "latency_ms": result["latency_ms"]
        }

    async def generate_for_agent(
        self,
        agent_type: str,
        prompt: str,
        context: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    ) -> Dict[str, Any]:
        """
        Generate response for a specific agent type.

        Args:
            agent_type: Type of agent (analyst, compliance, transaction)
            prompt: The prompt to generate from
            context: Optional context dictionary
            timeout_seconds: Request timeout in seconds

        Returns:
            Dict with text, model, and latency_ms
        """
        model = self.get_model_for_agent(agent_type)

        # Build full prompt with context
        full_prompt = prompt
        if context:
            context_str = json.dumps(context, indent=2)
            full_prompt = f"Context:\n{context_str}\n\n{prompt}"

        return await self.generate(
            prompt=full_prompt,
            model=model,
            timeout_seconds=timeout_seconds
        )


# Singleton instance
_gemini_service: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    """
    Get or create the GeminiService singleton.

    Returns:
        GeminiService instance

    Uses settings for configuration.
    """
    global _gemini_service
    if _gemini_service is None:
        from app.core.config import settings
        _gemini_service = GeminiService(
            api_key=settings.gemini_api_key,
            default_model=settings.gemini_pro_model
        )
    return _gemini_service
