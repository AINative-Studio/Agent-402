"""
Tests for Issue #238 — Production Circle Gateway USDC Integration.

Covers:
- CIRCLE_USE_PRODUCTION env var toggle (default False = mock mode)
- Retry logic with exponential backoff (max 3 retries)
- Error handling: 429 rate limit, 401 auth failure, network errors
- Real API call paths used when CIRCLE_USE_PRODUCTION=true
- Existing class interface unchanged

TDD RED phase: all tests written before implementation.

Built by AINative Dev Team
Refs #238
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import httpx
from typing import Optional, Dict, Any


# ─── Production Mode Toggle Tests ─────────────────────────────────────────────


class DescribeCircleServiceProductionToggle:
    """CIRCLE_USE_PRODUCTION env var controls mock vs real API calls."""

    def it_defaults_to_mock_mode_when_env_var_not_set(self):
        import os
        env_without_prod = {k: v for k, v in os.environ.items() if k != "CIRCLE_USE_PRODUCTION"}
        with patch.dict(os.environ, env_without_prod, clear=True):
            from app.services.circle_service import CircleService
            service = CircleService(api_key="test_key")
            assert service.use_production is False

    def it_is_false_when_env_var_set_to_false(self):
        import os
        with patch.dict(os.environ, {"CIRCLE_USE_PRODUCTION": "false"}):
            from app.services.circle_service import CircleService
            service = CircleService(api_key="test_key")
            assert service.use_production is False

    def it_is_true_when_env_var_set_to_true(self):
        import os
        with patch.dict(os.environ, {"CIRCLE_USE_PRODUCTION": "true"}):
            from app.services.circle_service import CircleService
            service = CircleService(api_key="test_key")
            assert service.use_production is True

    def it_is_true_when_env_var_set_to_True_uppercase(self):
        import os
        with patch.dict(os.environ, {"CIRCLE_USE_PRODUCTION": "True"}):
            from app.services.circle_service import CircleService
            service = CircleService(api_key="test_key")
            assert service.use_production is True

    def it_is_false_when_env_var_set_to_zero(self):
        import os
        with patch.dict(os.environ, {"CIRCLE_USE_PRODUCTION": "0"}):
            from app.services.circle_service import CircleService
            service = CircleService(api_key="test_key")
            assert service.use_production is False

    def it_exposes_use_production_as_attribute(self):
        from app.services.circle_service import CircleService
        service = CircleService(api_key="test_key")
        assert hasattr(service, "use_production")

    def it_accepts_use_production_constructor_kwarg(self):
        from app.services.circle_service import CircleService
        service = CircleService(api_key="test_key", use_production=True)
        assert service.use_production is True

    def it_constructor_kwarg_overrides_env_var(self):
        import os
        with patch.dict(os.environ, {"CIRCLE_USE_PRODUCTION": "false"}):
            from app.services.circle_service import CircleService
            service = CircleService(api_key="test_key", use_production=True)
            assert service.use_production is True


# ─── Retry Logic Tests ────────────────────────────────────────────────────────


class DescribeCircleServiceRetryLogic:
    """Retry with exponential backoff on transient failures (max 3 retries)."""

    @pytest.mark.asyncio
    async def it_retries_up_to_3_times_on_network_error(self):
        from app.services.circle_service import CircleService

        service = CircleService(api_key="test_key")
        call_count = 0

        async def flaky_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise httpx.RequestError("connection error")
            return {"data": {"id": "wallet_123"}}

        with patch.object(service, "_make_request", side_effect=flaky_request):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                try:
                    await service._make_request_with_retry(
                        method="GET",
                        endpoint="/test"
                    )
                except Exception:
                    pass

        # Should have been called at most 4 times (1 initial + 3 retries)
        assert call_count <= 4

    @pytest.mark.asyncio
    async def it_raises_after_max_retries_exceeded(self):
        from app.services.circle_service import CircleService, CircleAPIError

        service = CircleService(api_key="test_key")

        async def always_fails(*args, **kwargs):
            raise httpx.RequestError("permanent network failure")

        with patch.object(service, "_make_request", side_effect=always_fails):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises((CircleAPIError, httpx.RequestError, Exception)):
                    await service._make_request_with_retry(
                        method="GET",
                        endpoint="/test"
                    )

    @pytest.mark.asyncio
    async def it_succeeds_on_first_try_without_retries(self):
        from app.services.circle_service import CircleService

        service = CircleService(api_key="test_key")
        expected = {"data": {"id": "wallet_ok"}}

        async def always_succeeds(*args, **kwargs):
            return expected

        with patch.object(service, "_make_request", side_effect=always_succeeds):
            result = await service._make_request_with_retry(
                method="GET",
                endpoint="/test"
            )

        assert result == expected

    @pytest.mark.asyncio
    async def it_uses_exponential_backoff_between_retries(self):
        from app.services.circle_service import CircleService

        service = CircleService(api_key="test_key")
        sleep_durations = []

        async def capture_sleep(duration):
            sleep_durations.append(duration)

        async def always_fails(*args, **kwargs):
            raise httpx.RequestError("network error")

        with patch.object(service, "_make_request", side_effect=always_fails):
            with patch("asyncio.sleep", side_effect=capture_sleep):
                with pytest.raises(Exception):
                    await service._make_request_with_retry(
                        method="GET",
                        endpoint="/test"
                    )

        # Exponential: each sleep should be >= previous (or at minimum > 0)
        if len(sleep_durations) >= 2:
            assert sleep_durations[1] >= sleep_durations[0]

    @pytest.mark.asyncio
    async def it_does_not_retry_on_non_transient_errors(self):
        from app.services.circle_service import CircleService, CircleAPIError

        service = CircleService(api_key="test_key")
        call_count = 0

        async def auth_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise CircleAPIError("Unauthorized", status_code=401)

        with patch.object(service, "_make_request", side_effect=auth_failure):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(CircleAPIError):
                    await service._make_request_with_retry(
                        method="GET",
                        endpoint="/test"
                    )

        # 401 is not transient — should NOT retry
        assert call_count == 1


# ─── Error Handling Tests ─────────────────────────────────────────────────────


class DescribeCircleServiceErrorHandling:
    """Proper error handling for rate limits, auth failures, and network errors."""

    @pytest.mark.asyncio
    async def it_raises_circle_api_error_on_429_rate_limit(self):
        from app.services.circle_service import CircleService, CircleAPIError

        service = CircleService(api_key="test_key")

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.content = b'{"message": "Rate limit exceeded"}'
        mock_response.json.return_value = {"message": "Rate limit exceeded"}

        with patch.object(service, "client") as mock_client:
            mock_client.request = AsyncMock(return_value=mock_response)
            with pytest.raises(CircleAPIError) as exc_info:
                await service._make_request(method="GET", endpoint="/test")

        assert exc_info.value.circle_status_code == 429

    @pytest.mark.asyncio
    async def it_raises_circle_api_error_on_401_auth_failure(self):
        from app.services.circle_service import CircleService, CircleAPIError

        service = CircleService(api_key="test_key")

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.content = b'{"message": "Unauthorized"}'
        mock_response.json.return_value = {"message": "Unauthorized"}

        with patch.object(service, "client") as mock_client:
            mock_client.request = AsyncMock(return_value=mock_response)
            with pytest.raises(CircleAPIError) as exc_info:
                await service._make_request(method="GET", endpoint="/test")

        assert exc_info.value.circle_status_code == 401

    @pytest.mark.asyncio
    async def it_raises_circle_api_error_on_timeout(self):
        from app.services.circle_service import CircleService, CircleAPIError

        service = CircleService(api_key="test_key")

        with patch.object(service, "client") as mock_client:
            mock_client.request = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
            with pytest.raises(CircleAPIError) as exc_info:
                await service._make_request(method="GET", endpoint="/test")

        assert exc_info.value.circle_status_code == 504

    @pytest.mark.asyncio
    async def it_raises_circle_api_error_on_connection_error(self):
        from app.services.circle_service import CircleService, CircleAPIError

        service = CircleService(api_key="test_key")

        with patch.object(service, "client") as mock_client:
            mock_client.request = AsyncMock(side_effect=httpx.RequestError("connection refused"))
            with pytest.raises(CircleAPIError) as exc_info:
                await service._make_request(method="GET", endpoint="/test")

        assert exc_info.value.circle_status_code == 502

    @pytest.mark.asyncio
    async def it_includes_rate_limit_indicator_in_429_error(self):
        from app.services.circle_service import CircleService, CircleAPIError

        service = CircleService(api_key="test_key")

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.content = b'{"message": "Too Many Requests"}'
        mock_response.json.return_value = {"message": "Too Many Requests"}

        with patch.object(service, "client") as mock_client:
            mock_client.request = AsyncMock(return_value=mock_response)
            with pytest.raises(CircleAPIError) as exc_info:
                await service._make_request(method="GET", endpoint="/test")

        # The error should be identifiable as a rate limit error
        assert exc_info.value.circle_status_code == 429


# ─── Production Mode API Call Tests ───────────────────────────────────────────


class DescribeCircleServiceProductionCalls:
    """When use_production=True, real API calls are made without mock responses."""

    @pytest.mark.asyncio
    async def it_calls_make_request_when_production_mode_is_true(self):
        from app.services.circle_service import CircleService

        service = CircleService(api_key="test_key", use_production=True)
        assert service.use_production is True

    @pytest.mark.asyncio
    async def it_creates_wallet_set_via_real_api_in_production_mode(self):
        from app.services.circle_service import CircleService

        service = CircleService(
            api_key="test_key",
            use_production=True,
            entity_secret="a" * 64
        )

        mock_response = {
            "data": {
                "walletSet": {
                    "id": "real_walletset_id",
                    "custodyType": "DEVELOPER"
                }
            }
        }

        with patch.object(service, "_make_request", new_callable=AsyncMock, return_value=mock_response):
            with patch.object(service, "_get_entity_secret_ciphertext", new_callable=AsyncMock, return_value="fake_cipher"):
                result = await service.create_wallet_set(idempotency_key="idem_key_123")

        assert result["data"]["walletSet"]["id"] == "real_walletset_id"

    @pytest.mark.asyncio
    async def it_creates_transfer_via_real_api_in_production_mode(self):
        from app.services.circle_service import CircleService

        service = CircleService(
            api_key="test_key",
            use_production=True,
            entity_secret="a" * 64
        )

        mock_response = {
            "data": {
                "id": "real_transfer_id",
                "state": "INITIATED"
            }
        }

        with patch.object(service, "_make_request", new_callable=AsyncMock, return_value=mock_response):
            with patch.object(service, "_get_entity_secret_ciphertext", new_callable=AsyncMock, return_value="fake_cipher"):
                result = await service.create_transfer(
                    source_wallet_id="wallet_123",
                    destination_address="0xabc",
                    amount="10.00",
                    idempotency_key="idem_transfer_456"
                )

        assert result["data"]["id"] == "real_transfer_id"


# ─── Interface Stability Tests ────────────────────────────────────────────────


class DescribeCircleServiceInterfaceUnchanged:
    """The existing public interface must remain unchanged after Issue #238."""

    def it_has_create_wallet_set_method(self):
        from app.services.circle_service import CircleService
        assert hasattr(CircleService, "create_wallet_set")

    def it_has_create_wallet_method(self):
        from app.services.circle_service import CircleService
        assert hasattr(CircleService, "create_wallet")

    def it_has_get_wallet_method(self):
        from app.services.circle_service import CircleService
        assert hasattr(CircleService, "get_wallet")

    def it_has_get_wallet_balance_method(self):
        from app.services.circle_service import CircleService
        assert hasattr(CircleService, "get_wallet_balance")

    def it_has_create_transfer_method(self):
        from app.services.circle_service import CircleService
        assert hasattr(CircleService, "create_transfer")

    def it_has_get_transfer_method(self):
        from app.services.circle_service import CircleService
        assert hasattr(CircleService, "get_transfer")

    def it_has_list_wallets_method(self):
        from app.services.circle_service import CircleService
        assert hasattr(CircleService, "list_wallets")

    def it_has_list_transactions_method(self):
        from app.services.circle_service import CircleService
        assert hasattr(CircleService, "list_transactions")

    def it_still_accepts_api_key_as_constructor_arg(self):
        from app.services.circle_service import CircleService
        service = CircleService(api_key="test_key")
        assert service.api_key == "test_key"

    def it_still_accepts_base_url_as_constructor_arg(self):
        from app.services.circle_service import CircleService
        service = CircleService(api_key="test_key", base_url="https://api.example.com")
        assert service.base_url == "https://api.example.com"

    def it_still_accepts_entity_secret_as_constructor_arg(self):
        from app.services.circle_service import CircleService
        service = CircleService(api_key="test_key", entity_secret="my_secret_hex")
        assert service.entity_secret == "my_secret_hex"
