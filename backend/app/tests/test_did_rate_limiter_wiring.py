"""
Tests for DID-based rate limiter wiring.
Issue #241: DID-Based Rate Limiting Enforcement

TDD RED phase — tests written before implementation.
BDD-style: DescribeX / it_does_something

Built by AINative Dev Team
Refs #241
"""
from __future__ import annotations

import json
import base64
import pytest
from typing import Optional, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_middleware(rate_limiter=None):
    """Return RateLimiterMiddleware with mocked dependencies."""
    from app.middleware.rate_limiter import RateLimiterMiddleware

    return RateLimiterMiddleware(
        app=MagicMock(),
        rate_limiter=rate_limiter or MagicMock(),
    )


def _build_jwt_token(sub: str) -> str:
    """Build a minimal unsigned JWT with a sub claim for testing."""
    header = base64.b64encode(b'{"alg":"none"}').decode().rstrip("=")
    payload_bytes = json.dumps({"sub": sub, "iat": 1700000000}).encode()
    payload = base64.b64encode(payload_bytes).decode().rstrip("=")
    return f"{header}.{payload}."


def _make_request(
    path: str = "/v1/public/agents",
    method: str = "POST",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
) -> MagicMock:
    """Build a mock FastAPI Request."""
    mock_request = MagicMock()
    mock_request.url.path = path
    mock_request.method = method
    mock_request.headers = headers or {}

    async def _json():
        return body or {}

    mock_request.json = _json
    return mock_request


# ---------------------------------------------------------------------------
# DescribeExtractDidFromX402Payload
# ---------------------------------------------------------------------------


class DescribeExtractDidFromX402Payload:
    """Describe RateLimiterMiddleware._extract_did_from_x402_payload behavior."""

    @pytest.mark.asyncio
    async def it_extracts_did_from_post_body(self):
        """DID from the 'did' field of a POST JSON body is returned."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        middleware = _make_middleware()
        request = _make_request(
            path="/x402",
            method="POST",
            body={"did": "did:hedera:testnet:agent-1", "payload": {}},
        )

        result = await middleware._extract_did_from_x402_payload(request)

        assert result == "did:hedera:testnet:agent-1"

    @pytest.mark.asyncio
    async def it_returns_none_when_body_has_no_did_field(self):
        """None is returned when the POST body lacks a 'did' field."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        middleware = _make_middleware()
        request = _make_request(
            path="/x402",
            method="POST",
            body={"payload": "some_data"},
        )

        result = await middleware._extract_did_from_x402_payload(request)

        assert result is None

    @pytest.mark.asyncio
    async def it_returns_none_when_body_is_not_json(self):
        """None is returned when the request body cannot be parsed as JSON."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        middleware = _make_middleware()
        mock_request = MagicMock()
        mock_request.url.path = "/x402"
        mock_request.method = "POST"
        mock_request.headers = {}

        async def _bad_json():
            raise ValueError("Not JSON")

        mock_request.json = _bad_json

        result = await middleware._extract_did_from_x402_payload(mock_request)

        assert result is None

    @pytest.mark.asyncio
    async def it_strips_whitespace_from_extracted_did(self):
        """Leading/trailing whitespace is stripped from the extracted DID."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        middleware = _make_middleware()
        request = _make_request(
            path="/x402",
            method="POST",
            body={"did": "  did:hedera:testnet:agent-padded  "},
        )

        result = await middleware._extract_did_from_x402_payload(request)

        assert result == "did:hedera:testnet:agent-padded"


# ---------------------------------------------------------------------------
# DescribeExtractDidFromJwt
# ---------------------------------------------------------------------------


class DescribeExtractDidFromJwt:
    """Describe RateLimiterMiddleware._extract_did_from_jwt behavior."""

    def it_extracts_sub_claim_from_bearer_token(self):
        """The 'sub' JWT claim is returned as the DID."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        middleware = _make_middleware()
        token = _build_jwt_token("did:hedera:testnet:agent-jwt")
        request = _make_request(
            headers={"Authorization": f"Bearer {token}"},
        )

        # Patch decode_access_token to return predictable data
        mock_token_data = MagicMock()
        mock_token_data.user_id = "did:hedera:testnet:agent-jwt"

        with patch(
            "app.middleware.rate_limiter.decode_access_token_sub",
            return_value="did:hedera:testnet:agent-jwt",
        ):
            result = middleware._extract_did_from_jwt(request)

        assert result == "did:hedera:testnet:agent-jwt"

    def it_returns_none_when_no_authorization_header(self):
        """None is returned when the Authorization header is absent."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        middleware = _make_middleware()
        request = _make_request(headers={})

        result = middleware._extract_did_from_jwt(request)

        assert result is None

    def it_returns_none_when_authorization_is_not_bearer(self):
        """Non-Bearer auth schemes (e.g., Basic) are not parsed for DID."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        middleware = _make_middleware()
        request = _make_request(headers={"Authorization": "Basic dXNlcjpwYXNz"})

        result = middleware._extract_did_from_jwt(request)

        assert result is None

    def it_returns_none_on_invalid_jwt(self):
        """An unparseable or structurally invalid JWT returns None (non-fatal)."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        middleware = _make_middleware()
        request = _make_request(
            headers={"Authorization": "Bearer this.is.garbage"}
        )

        with patch(
            "app.middleware.rate_limiter.decode_access_token_sub",
            side_effect=Exception("decode error"),
        ):
            result = middleware._extract_did_from_jwt(request)

        assert result is None


# ---------------------------------------------------------------------------
# DescribeDidExtractionPriority
# ---------------------------------------------------------------------------


class DescribeDidExtractionPriority:
    """Describe DID extraction priority: x402 payload > header > JWT."""

    @pytest.mark.asyncio
    async def it_prefers_x402_payload_did_over_header_did(self):
        """x402 payload DID takes priority over X-Agent-DID header."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        middleware = _make_middleware()
        request = _make_request(
            path="/x402",
            method="POST",
            headers={"X-Agent-DID": "did:hedera:testnet:header-agent"},
            body={"did": "did:hedera:testnet:payload-agent"},
        )

        result = await middleware._resolve_did(request)

        assert result == "did:hedera:testnet:payload-agent"

    @pytest.mark.asyncio
    async def it_falls_back_to_header_when_no_payload_did(self):
        """When x402 payload has no DID, the X-Agent-DID header is used."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        middleware = _make_middleware()
        request = _make_request(
            path="/x402",
            method="POST",
            headers={"X-Agent-DID": "did:hedera:testnet:header-agent"},
            body={"payload": "no did here"},
        )

        result = await middleware._resolve_did(request)

        assert result == "did:hedera:testnet:header-agent"

    @pytest.mark.asyncio
    async def it_falls_back_to_jwt_when_no_payload_or_header_did(self):
        """When neither payload nor header provide a DID, JWT sub is used."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        middleware = _make_middleware()
        request = _make_request(
            path="/x402",
            method="POST",
            headers={"Authorization": "Bearer some.jwt.token"},
            body={"payload": "no did here"},
        )

        with patch.object(
            RateLimiterMiddleware,
            "_extract_did_from_jwt",
            return_value="did:hedera:testnet:jwt-agent",
        ):
            result = await middleware._resolve_did(request)

        assert result == "did:hedera:testnet:jwt-agent"

    @pytest.mark.asyncio
    async def it_returns_none_when_no_did_source_available(self):
        """None is returned when none of the three DID sources contain a DID."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        middleware = _make_middleware()
        request = _make_request(
            path="/v1/public/agents",
            method="POST",
            headers={},
            body={},
        )

        result = await middleware._resolve_did(request)

        assert result is None

    @pytest.mark.asyncio
    async def it_returns_header_did_for_non_x402_paths(self):
        """Non-x402 POST requests use X-Agent-DID header (not body parsing)."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        middleware = _make_middleware()
        request = _make_request(
            path="/v1/public/agents",
            method="POST",
            headers={"X-Agent-DID": "did:hedera:testnet:header-agent"},
            body={"name": "my-agent"},
        )

        result = await middleware._resolve_did(request)

        assert result == "did:hedera:testnet:header-agent"


# ---------------------------------------------------------------------------
# DescribeRateLimitEventLogging
# ---------------------------------------------------------------------------


class DescribeRateLimitEventLogging:
    """Describe rate limit event logging to ZeroDB for analytics."""

    @pytest.mark.asyncio
    async def it_logs_rate_limit_event_to_zerodb_on_limit_exceeded(self):
        """When rate limit is exceeded, an analytics event is logged to ZeroDB."""
        from app.middleware.rate_limiter import RateLimiterMiddleware
        from app.core.errors import RateLimitExceededError

        mock_limiter = AsyncMock()
        mock_limiter.check_rate_limit = AsyncMock(
            side_effect=RateLimitExceededError(
                did="did:hedera:testnet:agent-1",
                retry_after_seconds=30,
            )
        )
        mock_limiter.log_rate_limit_event = AsyncMock(return_value=None)

        middleware = _make_middleware(rate_limiter=mock_limiter)
        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        request = _make_request(
            path="/v1/public/agents",
            headers={"X-Agent-DID": "did:hedera:testnet:agent-1"},
        )

        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 429
        mock_limiter.log_rate_limit_event.assert_called_once()

    @pytest.mark.asyncio
    async def it_does_not_log_when_request_is_allowed(self):
        """No analytics event is logged for allowed (non-limited) requests."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        mock_limiter = AsyncMock()
        mock_limiter.check_rate_limit = AsyncMock(return_value=True)
        mock_limiter.log_rate_limit_event = AsyncMock(return_value=None)

        middleware = _make_middleware(rate_limiter=mock_limiter)
        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        request = _make_request(
            path="/v1/public/agents",
            headers={"X-Agent-DID": "did:hedera:testnet:agent-1"},
        )

        await middleware.dispatch(request, mock_call_next)

        mock_limiter.log_rate_limit_event.assert_not_called()


# ---------------------------------------------------------------------------
# DescribeDispatchWithNewDIDExtraction
# ---------------------------------------------------------------------------


class DescribeDispatchWithNewDIDExtraction:
    """Describe full dispatch flow using the new three-source DID resolution."""

    @pytest.mark.asyncio
    async def it_uses_x402_payload_did_for_rate_limiting(self):
        """The DID from the x402 POST body is used as the rate-limit key."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        mock_limiter = AsyncMock()
        mock_limiter.check_rate_limit = AsyncMock(return_value=True)
        mock_limiter.log_rate_limit_event = AsyncMock(return_value=None)

        middleware = RateLimiterMiddleware(
            app=MagicMock(),
            rate_limiter=mock_limiter,
        )
        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        request = _make_request(
            path="/x402",
            method="POST",
            body={"did": "did:hedera:testnet:payload-agent"},
        )

        await middleware.dispatch(request, mock_call_next)

        mock_limiter.check_rate_limit.assert_called_once()
        call_kwargs = mock_limiter.check_rate_limit.call_args
        did_used = call_kwargs[1].get("did") or call_kwargs[0][0]
        assert did_used == "did:hedera:testnet:payload-agent"


# ---------------------------------------------------------------------------
# DescribeLegacyExtractDid
# ---------------------------------------------------------------------------


class DescribeLegacyExtractDid:
    """Describe RateLimiterMiddleware._extract_did (Sprint 2 legacy static method)."""

    def it_extracts_did_from_header(self):
        """The legacy _extract_did returns the X-Agent-DID header value."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        request = _make_request(headers={"X-Agent-DID": "did:hedera:testnet:legacy"})
        result = RateLimiterMiddleware._extract_did(request)
        assert result == "did:hedera:testnet:legacy"

    def it_returns_none_when_no_header_and_no_bearer(self):
        """_extract_did returns None when no header or Bearer token present."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        request = _make_request(headers={})
        result = RateLimiterMiddleware._extract_did(request)
        assert result is None

    def it_falls_back_to_jwt_sub_for_bearer_token(self):
        """_extract_did falls back to JWT sub claim when header is absent."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        request = _make_request(headers={"Authorization": "Bearer some.jwt.token"})
        with patch(
            "app.middleware.rate_limiter.decode_access_token_sub",
            return_value="did:hedera:testnet:jwt-legacy",
        ):
            result = RateLimiterMiddleware._extract_did(request)
        assert result == "did:hedera:testnet:jwt-legacy"


# ---------------------------------------------------------------------------
# DescribeDecodeAccessTokenSub
# ---------------------------------------------------------------------------


class DescribeDecodeAccessTokenSub:
    """Describe the module-level decode_access_token_sub helper."""

    def it_returns_none_when_decode_raises(self):
        """Returns None when the underlying decoder raises any exception."""
        from app.middleware.rate_limiter import decode_access_token_sub

        with patch(
            "app.middleware.rate_limiter.decode_access_token_sub",
            side_effect=Exception("jwt decode fail"),
        ):
            # Patching itself — call directly to exercise the real fallback path
            pass

        # Verify real function returns None on decode failure
        result = decode_access_token_sub("bad.token.here")
        assert result is None

    def it_returns_none_when_token_data_has_no_user_id(self):
        """Returns None when decoded token_data.user_id is falsy."""
        from app.middleware.rate_limiter import decode_access_token_sub

        mock_token_data = MagicMock()
        mock_token_data.user_id = None

        with patch(
            "app.core.jwt.decode_access_token",
            return_value=mock_token_data,
        ):
            result = decode_access_token_sub("some.valid.token")

        assert result is None


# ---------------------------------------------------------------------------
# DescribeExemptPaths
# ---------------------------------------------------------------------------


class DescribeExemptPaths:
    """Describe that exempt paths bypass rate limiting."""

    @pytest.mark.asyncio
    async def it_bypasses_rate_limit_for_health_path(self):
        """Requests to /health skip rate limiting entirely."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        mock_limiter = AsyncMock()
        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        middleware = RateLimiterMiddleware(app=MagicMock(), rate_limiter=mock_limiter)
        request = _make_request(path="/health")

        await middleware.dispatch(request, mock_call_next)

        mock_limiter.check_rate_limit.assert_not_called()
        mock_call_next.assert_called_once()

    @pytest.mark.asyncio
    async def it_bypasses_rate_limit_for_wellknown_x402_path(self):
        """GET /.well-known/x402 discovery endpoint bypasses rate limiting."""
        from app.middleware.rate_limiter import RateLimiterMiddleware

        mock_limiter = AsyncMock()
        mock_call_next = AsyncMock(return_value=MagicMock(status_code=200))

        middleware = RateLimiterMiddleware(app=MagicMock(), rate_limiter=mock_limiter)
        request = _make_request(path="/.well-known/x402")

        await middleware.dispatch(request, mock_call_next)

        mock_limiter.check_rate_limit.assert_not_called()
