"""
Unit tests for GeminiService.

TDD: These tests are written FIRST before implementation.
Tests follow BDD-style (describe/it) for clarity.

Coverage targets:
- Service initialization
- Model selection (gemini-pro, gemini-flash)
- Function calling with Circle tools
- Structured output parsing
- Rate limiting and retry logic
- Error handling

Issue #115: Gemini AI Integration
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
import asyncio
import time


# Create a custom exception to mock ResourceExhausted
class MockResourceExhausted(Exception):
    """Mock for google.api_core.exceptions.ResourceExhausted"""
    pass


class TestGeminiServiceInitialization:
    """Test GeminiService initialization and configuration."""

    def test_init_with_api_key(self):
        """It should initialize with API key from settings."""
        with patch('app.services.gemini_service.genai'):
            from app.services.gemini_service import GeminiService

            service = GeminiService(api_key="test_api_key")

            assert service.api_key == "test_api_key"
            assert service.default_model == "gemini-pro"

    def test_init_with_custom_model(self):
        """It should accept custom default model."""
        with patch('app.services.gemini_service.genai'):
            from app.services.gemini_service import GeminiService

            service = GeminiService(
                api_key="test_api_key",
                default_model="gemini-1.5-flash"
            )

            assert service.default_model == "gemini-1.5-flash"

    def test_init_without_api_key_raises(self):
        """It should raise error when API key is missing."""
        from app.services.gemini_service import GeminiService, GeminiConfigError

        with pytest.raises(GeminiConfigError) as exc_info:
            GeminiService(api_key="")

        assert exc_info.value.error_code == "GEMINI_CONFIG_ERROR"
        assert "API key" in str(exc_info.value.detail)

    def test_supported_models(self):
        """It should expose list of supported models."""
        from app.services.gemini_service import SUPPORTED_MODELS

        assert "gemini-pro" in SUPPORTED_MODELS
        assert "gemini-1.5-flash" in SUPPORTED_MODELS
        assert "gemini-1.5-pro" in SUPPORTED_MODELS


class TestGeminiModelSelection:
    """Test model selection for different agent types."""

    @pytest.fixture
    def service(self):
        """Create service instance for tests."""
        with patch('app.services.gemini_service.genai'):
            from app.services.gemini_service import GeminiService
            return GeminiService(api_key="test_api_key")

    def test_analyst_agent_uses_gemini_pro(self, service):
        """Analyst agent should use gemini-pro for deep analysis."""
        model = service.get_model_for_agent("analyst")
        assert model == "gemini-pro"

    def test_compliance_agent_uses_gemini_pro(self, service):
        """Compliance agent should use gemini-pro for thorough checks."""
        model = service.get_model_for_agent("compliance")
        assert model == "gemini-pro"

    def test_transaction_agent_uses_gemini_flash(self, service):
        """Transaction agent should use gemini-flash for fast execution."""
        model = service.get_model_for_agent("transaction")
        assert model == "gemini-1.5-flash"

    def test_unknown_agent_uses_default(self, service):
        """Unknown agent type should use default model."""
        model = service.get_model_for_agent("unknown")
        assert model == "gemini-pro"


class TestGeminiGeneration:
    """Test text generation capabilities."""

    @pytest.fixture
    def mock_genai(self):
        """Mock google.generativeai module."""
        with patch('app.services.gemini_service.genai') as mock:
            yield mock

    @pytest.fixture
    def service(self, mock_genai):
        """Create service with mocked genai."""
        from app.services.gemini_service import GeminiService
        return GeminiService(api_key="test_api_key")

    @pytest.mark.asyncio
    async def test_generate_text_success(self, service, mock_genai):
        """It should generate text from prompt."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Generated response"
        mock_response.prompt_feedback = None  # No safety block
        mock_response.candidates = [MagicMock()]
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        result = await service.generate(
            prompt="Test prompt",
            model="gemini-pro"
        )

        assert result["text"] == "Generated response"
        assert result["model"] == "gemini-pro"
        assert "latency_ms" in result

    @pytest.mark.asyncio
    async def test_generate_with_system_instruction(self, service, mock_genai):
        """It should include system instruction when provided."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Response with context"
        mock_response.prompt_feedback = None
        mock_response.candidates = [MagicMock()]
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        result = await service.generate(
            prompt="Test prompt",
            system_instruction="You are a helpful assistant"
        )

        mock_genai.GenerativeModel.assert_called_once()
        call_kwargs = mock_genai.GenerativeModel.call_args[1]
        assert call_kwargs.get("system_instruction") == "You are a helpful assistant"

    @pytest.mark.asyncio
    async def test_generate_respects_timeout(self, service, mock_genai):
        """It should timeout if response takes too long."""
        from app.services.gemini_service import GeminiTimeoutError

        mock_model = MagicMock()

        async def slow_response(*args, **kwargs):
            await asyncio.sleep(10)
            return MagicMock(text="Too late")

        mock_model.generate_content_async = slow_response
        mock_genai.GenerativeModel.return_value = mock_model

        with pytest.raises(GeminiTimeoutError) as exc_info:
            await service.generate(
                prompt="Test prompt",
                timeout_seconds=0.1
            )

        assert exc_info.value.error_code == "GEMINI_TIMEOUT"

    @pytest.mark.asyncio
    async def test_generate_under_5_seconds(self, service, mock_genai):
        """It should complete response within 5 seconds requirement."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Fast response"
        mock_response.prompt_feedback = None
        mock_response.candidates = [MagicMock()]
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        start = time.time()
        result = await service.generate(prompt="Test prompt")
        elapsed = time.time() - start

        assert elapsed < 5.0
        assert result["latency_ms"] < 5000


class TestGeminiFunctionCalling:
    """Test function calling support for Circle tools."""

    @pytest.fixture
    def mock_genai(self):
        """Mock google.generativeai module."""
        with patch('app.services.gemini_service.genai') as mock:
            yield mock

    @pytest.fixture
    def service(self, mock_genai):
        """Create service with mocked genai."""
        from app.services.gemini_service import GeminiService
        return GeminiService(api_key="test_api_key")

    @pytest.fixture
    def circle_tools(self):
        """Define Circle tool schemas."""
        return [
            {
                "name": "create_wallet",
                "description": "Create a new Circle wallet",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "blockchain": {
                            "type": "string",
                            "description": "Target blockchain"
                        }
                    }
                }
            },
            {
                "name": "transfer_usdc",
                "description": "Transfer USDC between wallets",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "source_wallet_id": {"type": "string"},
                        "destination_wallet_id": {"type": "string"},
                        "amount": {"type": "string"}
                    },
                    "required": ["source_wallet_id", "destination_wallet_id", "amount"]
                }
            },
            {
                "name": "get_wallet_balance",
                "description": "Get USDC balance for a wallet",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "wallet_id": {"type": "string"}
                    },
                    "required": ["wallet_id"]
                }
            }
        ]

    @pytest.mark.asyncio
    async def test_function_calling_with_tools(self, service, mock_genai, circle_tools):
        """It should support function calling with Circle tools."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_function_call = MagicMock()
        mock_function_call.name = "create_wallet"
        mock_function_call.args = {"blockchain": "ETH-SEPOLIA"}
        mock_response.candidates = [
            MagicMock(content=MagicMock(parts=[
                MagicMock(function_call=mock_function_call)
            ]))
        ]
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        result = await service.generate_with_tools(
            prompt="Create a new wallet on Sepolia",
            tools=circle_tools
        )

        assert result["function_call"]["name"] == "create_wallet"
        assert result["function_call"]["args"]["blockchain"] == "ETH-SEPOLIA"

    @pytest.mark.asyncio
    async def test_function_calling_transfer_usdc(self, service, mock_genai, circle_tools):
        """It should call transfer_usdc with correct parameters."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_function_call = MagicMock()
        mock_function_call.name = "transfer_usdc"
        mock_function_call.args = {
            "source_wallet_id": "wallet_123",
            "destination_wallet_id": "wallet_456",
            "amount": "100.00"
        }
        mock_response.candidates = [
            MagicMock(content=MagicMock(parts=[
                MagicMock(function_call=mock_function_call)
            ]))
        ]
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        result = await service.generate_with_tools(
            prompt="Transfer 100 USDC from wallet_123 to wallet_456",
            tools=circle_tools
        )

        assert result["function_call"]["name"] == "transfer_usdc"
        assert result["function_call"]["args"]["amount"] == "100.00"

    @pytest.mark.asyncio
    async def test_function_calling_no_match(self, service, mock_genai, circle_tools):
        """It should return text response when no function matches."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "I cannot perform that operation."
        mock_response.candidates = [
            MagicMock(content=MagicMock(parts=[
                MagicMock(function_call=None, text="I cannot perform that operation.")
            ]))
        ]
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        result = await service.generate_with_tools(
            prompt="What is the weather?",
            tools=circle_tools
        )

        assert result.get("function_call") is None
        assert "text" in result

    def test_convert_tools_to_gemini_format(self, service, circle_tools):
        """It should convert tool definitions to Gemini format."""
        gemini_tools = service.convert_tools_to_gemini_format(circle_tools)

        assert len(gemini_tools) == 3
        assert gemini_tools[0]["name"] == "create_wallet"
        assert "parameters" in gemini_tools[0]


class TestGeminiStructuredOutput:
    """Test structured output parsing."""

    @pytest.fixture
    def mock_genai(self):
        """Mock google.generativeai module."""
        with patch('app.services.gemini_service.genai') as mock:
            yield mock

    @pytest.fixture
    def service(self, mock_genai):
        """Create service with mocked genai."""
        from app.services.gemini_service import GeminiService
        return GeminiService(api_key="test_api_key")

    @pytest.mark.asyncio
    async def test_parse_json_response(self, service, mock_genai):
        """It should parse JSON from response text."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"status": "approved", "risk_score": 0.2}'
        mock_response.prompt_feedback = None
        mock_response.candidates = [MagicMock()]
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        result = await service.generate_structured(
            prompt="Analyze this transaction",
            response_schema={
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "risk_score": {"type": "number"}
                }
            }
        )

        assert result["parsed"]["status"] == "approved"
        assert result["parsed"]["risk_score"] == 0.2

    @pytest.mark.asyncio
    async def test_parse_json_with_code_block(self, service, mock_genai):
        """It should extract JSON from markdown code blocks."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '''Here is the analysis:
```json
{"status": "approved", "risk_score": 0.2}
```'''
        mock_response.prompt_feedback = None
        mock_response.candidates = [MagicMock()]
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        result = await service.generate_structured(
            prompt="Analyze this transaction",
            response_schema={}
        )

        assert result["parsed"]["status"] == "approved"

    @pytest.mark.asyncio
    async def test_invalid_json_returns_error(self, service, mock_genai):
        """It should handle invalid JSON gracefully."""
        from app.services.gemini_service import GeminiParseError

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON"
        mock_response.prompt_feedback = None
        mock_response.candidates = [MagicMock()]
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        with pytest.raises(GeminiParseError) as exc_info:
            await service.generate_structured(
                prompt="Analyze this transaction",
                response_schema={}
            )

        assert exc_info.value.error_code == "GEMINI_PARSE_ERROR"


class TestGeminiRateLimiting:
    """Test rate limiting and retry logic."""

    @pytest.fixture
    def mock_genai(self):
        """Mock google.generativeai module."""
        with patch('app.services.gemini_service.genai') as mock:
            yield mock

    @pytest.fixture
    def service(self, mock_genai):
        """Create service with mocked genai."""
        from app.services.gemini_service import GeminiService
        return GeminiService(api_key="test_api_key")

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, service, mock_genai):
        """It should retry on rate limit errors."""
        mock_model = MagicMock()

        call_count = 0

        async def rate_limited_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise MockResourceExhausted("Rate limit exceeded")
            mock_response = MagicMock()
            mock_response.text = "Success after retry"
            mock_response.prompt_feedback = None
            mock_response.candidates = [MagicMock()]
            return mock_response

        mock_model.generate_content_async = rate_limited_then_success
        mock_genai.GenerativeModel.return_value = mock_model

        # Patch ResourceExhausted to be our mock exception
        with patch('app.services.gemini_service.ResourceExhausted', MockResourceExhausted):
            result = await service.generate(
                prompt="Test prompt",
                max_retries=5
            )

        assert call_count == 3
        assert result["text"] == "Success after retry"

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, service, mock_genai):
        """It should fail after max retries exceeded."""
        from app.services.gemini_service import GeminiRateLimitError

        mock_model = MagicMock()

        async def always_rate_limited(*args, **kwargs):
            raise MockResourceExhausted("Rate limit exceeded")

        mock_model.generate_content_async = always_rate_limited
        mock_genai.GenerativeModel.return_value = mock_model

        with patch('app.services.gemini_service.ResourceExhausted', MockResourceExhausted):
            with pytest.raises(GeminiRateLimitError) as exc_info:
                await service.generate(
                    prompt="Test prompt",
                    max_retries=2
                )

        assert exc_info.value.error_code == "GEMINI_RATE_LIMIT"

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, service, mock_genai):
        """It should use exponential backoff between retries."""
        mock_model = MagicMock()

        timestamps = []
        call_count = 0

        async def track_timing(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            timestamps.append(time.time())
            if call_count < 3:
                raise MockResourceExhausted("Rate limit")
            mock_response = MagicMock()
            mock_response.text = "Success"
            mock_response.prompt_feedback = None
            mock_response.candidates = [MagicMock()]
            return mock_response

        mock_model.generate_content_async = track_timing
        mock_genai.GenerativeModel.return_value = mock_model

        with patch('app.services.gemini_service.ResourceExhausted', MockResourceExhausted):
            await service.generate(prompt="Test", max_retries=5)

        # Check that delays increase (exponential backoff)
        if len(timestamps) >= 3:
            delay1 = timestamps[1] - timestamps[0]
            delay2 = timestamps[2] - timestamps[1]
            # Second delay should be roughly 2x the first
            assert delay2 >= delay1 * 1.5


class TestGeminiErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def mock_genai(self):
        """Mock google.generativeai module."""
        with patch('app.services.gemini_service.genai') as mock:
            yield mock

    @pytest.fixture
    def service(self, mock_genai):
        """Create service with mocked genai."""
        from app.services.gemini_service import GeminiService
        return GeminiService(api_key="test_api_key")

    @pytest.mark.asyncio
    async def test_api_error_handling(self, service, mock_genai):
        """It should wrap API errors appropriately."""
        from app.services.gemini_service import GeminiAPIError

        # Create a custom error class that is NOT ResourceExhausted
        class CustomAPIError(ValueError):
            pass

        mock_model = MagicMock()
        mock_model.generate_content_async = AsyncMock(
            side_effect=CustomAPIError("API Error")
        )
        mock_genai.GenerativeModel.return_value = mock_model

        # Patch ResourceExhausted to a different exception type
        # so our CustomAPIError is not caught by it
        with patch('app.services.gemini_service.ResourceExhausted', MockResourceExhausted):
            with pytest.raises(GeminiAPIError) as exc_info:
                await service.generate(prompt="Test")

        assert exc_info.value.error_code == "GEMINI_API_ERROR"
        assert "API Error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_invalid_model_error(self, service):
        """It should error on invalid model selection."""
        from app.services.gemini_service import GeminiModelError

        with pytest.raises(GeminiModelError) as exc_info:
            await service.generate(
                prompt="Test",
                model="invalid-model-name"
            )

        assert exc_info.value.error_code == "GEMINI_MODEL_ERROR"

    @pytest.mark.asyncio
    async def test_empty_response_handling(self, service, mock_genai):
        """It should handle empty responses gracefully."""
        from app.services.gemini_service import GeminiEmptyResponseError

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.prompt_feedback = None
        mock_response.candidates = []
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        with pytest.raises(GeminiEmptyResponseError) as exc_info:
            await service.generate(prompt="Test")

        assert exc_info.value.error_code == "GEMINI_EMPTY_RESPONSE"

    @pytest.mark.asyncio
    async def test_safety_block_handling(self, service, mock_genai):
        """It should handle safety-blocked responses."""
        from app.services.gemini_service import GeminiSafetyError

        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = None
        mock_response.candidates = []
        mock_response.prompt_feedback = MagicMock()
        mock_response.prompt_feedback.block_reason = "SAFETY"  # String, not MagicMock
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        with pytest.raises(GeminiSafetyError) as exc_info:
            await service.generate(prompt="Test")

        assert exc_info.value.error_code == "GEMINI_SAFETY_BLOCK"


class TestGeminiAgentIntegration:
    """Test integration with CrewAI agents."""

    @pytest.fixture
    def mock_genai(self):
        """Mock google.generativeai module."""
        with patch('app.services.gemini_service.genai') as mock:
            yield mock

    @pytest.fixture
    def service(self, mock_genai):
        """Create service with mocked genai."""
        from app.services.gemini_service import GeminiService
        return GeminiService(api_key="test_api_key")

    @pytest.mark.asyncio
    async def test_analyst_agent_prompt(self, service, mock_genai):
        """It should generate analysis for analyst agent."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"market_data": {"price": 1.0}, "recommendation": "buy"}'
        mock_response.prompt_feedback = None
        mock_response.candidates = [MagicMock()]
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        result = await service.generate_for_agent(
            agent_type="analyst",
            prompt="Analyze USDC market conditions",
            context={"current_price": 1.0}
        )

        assert "market_data" in result["text"] or "recommendation" in result["text"]
        assert result["model"] == "gemini-pro"

    @pytest.mark.asyncio
    async def test_compliance_agent_prompt(self, service, mock_genai):
        """It should generate compliance check for compliance agent."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"approved": true, "risk_score": 0.15, "checks_passed": ["aml", "kyc"]}'
        mock_response.prompt_feedback = None
        mock_response.candidates = [MagicMock()]
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        result = await service.generate_for_agent(
            agent_type="compliance",
            prompt="Check this transaction for compliance",
            context={"amount": "1000.00", "sender": "wallet_123"}
        )

        assert result["model"] == "gemini-pro"

    @pytest.mark.asyncio
    async def test_transaction_agent_prompt(self, service, mock_genai):
        """It should generate transaction execution for transaction agent."""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"action": "execute", "transaction_id": "tx_123"}'
        mock_response.prompt_feedback = None
        mock_response.candidates = [MagicMock()]
        mock_model.generate_content_async = AsyncMock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model

        result = await service.generate_for_agent(
            agent_type="transaction",
            prompt="Execute approved transfer",
            context={"approved": True, "amount": "500.00"}
        )

        assert result["model"] == "gemini-1.5-flash"


class TestLLMServiceAbstraction:
    """Test LLM service abstraction layer."""

    def test_llm_service_interface(self):
        """It should define LLMService interface."""
        from app.services.llm_service import LLMService

        # Interface should define abstract methods
        assert hasattr(LLMService, 'generate')
        assert hasattr(LLMService, 'generate_with_tools')
        assert hasattr(LLMService, 'generate_structured')

    def test_gemini_adapter_implements_interface(self):
        """GeminiLLMAdapter should implement LLMService interface."""
        with patch('app.services.gemini_service.genai'):
            from app.services.llm_service import LLMService, GeminiLLMAdapter

            adapter = GeminiLLMAdapter(api_key="test_key")

            assert isinstance(adapter, LLMService)

    @pytest.mark.asyncio
    async def test_adapter_delegates_to_gemini_service(self):
        """Adapter should delegate calls to GeminiService."""
        with patch('app.services.gemini_service.genai') as mock_genai:
            # Setup mock model and response
            mock_model = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "response"
            mock_response.prompt_feedback = None
            mock_response.candidates = [MagicMock()]
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)
            mock_genai.GenerativeModel.return_value = mock_model

            from app.services.llm_service import GeminiLLMAdapter

            adapter = GeminiLLMAdapter(api_key="test_key")
            result = await adapter.generate(prompt="Test")

            assert result["text"] == "response"


class TestGeminiServiceFactory:
    """Test factory functions for service creation."""

    def test_get_gemini_service_from_settings(self):
        """It should create service from settings."""
        with patch('app.services.gemini_service.genai'):
            with patch('app.core.config.settings') as mock_settings:
                mock_settings.gemini_api_key = "settings_api_key"
                mock_settings.gemini_pro_model = "gemini-pro"
                mock_settings.gemini_flash_model = "gemini-1.5-flash"

                # Reset singleton
                import app.services.gemini_service as gem_mod
                gem_mod._gemini_service = None

                from app.services.gemini_service import get_gemini_service

                service = get_gemini_service()

                assert service.api_key == "settings_api_key"

                # Reset singleton again
                gem_mod._gemini_service = None

    def test_get_llm_service_returns_gemini_adapter(self):
        """It should return GeminiLLMAdapter by default."""
        with patch('app.services.gemini_service.genai'):
            with patch('app.core.config.settings') as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_pro_model = "gemini-pro"
                mock_settings.llm_provider = "gemini"

                # Reset singleton
                import app.services.llm_service as llm_mod
                llm_mod._llm_service = None

                from app.services.llm_service import get_llm_service

                service = get_llm_service()

                assert service.__class__.__name__ == "GeminiLLMAdapter"

                # Reset singleton again
                llm_mod._llm_service = None
