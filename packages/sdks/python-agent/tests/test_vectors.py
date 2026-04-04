"""
Tests for ainative_agent.vectors — VectorOperations.

Describes: upsert with dimension validation, search, and delete.

Built by AINative Dev Team.
"""
from __future__ import annotations

import pytest

from ainative_agent.errors import DimensionError, NotFoundError
from ainative_agent.types import Vector, VectorSearchResult
from tests.conftest import make_response

# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

EMBEDDING_384 = [0.1] * 384
EMBEDDING_768 = [0.2] * 768
EMBEDDING_1024 = [0.3] * 1024
EMBEDDING_1536 = [0.4] * 1536
EMBEDDING_INVALID = [0.5] * 512  # not supported

VECTOR_PAYLOAD = {
    "id": "vec_abc1234567890123",
    "embedding": EMBEDDING_384,
    "metadata": {
        "document": "sample document",
        "model": "BAAI/bge-small-en-v1.5",
        "namespace": "default",
        "extra": {},
    },
    "created": True,
}

VECTOR_SEARCH_RESULT = {
    "id": "vec_abc1234567890123",
    "score": 0.87,
    "metadata": {
        "document": "sample document",
        "model": "BAAI/bge-small-en-v1.5",
        "namespace": "default",
        "extra": {},
    },
}


# ---------------------------------------------------------------------------
# describe: VectorOperations.upsert — dimension validation
# ---------------------------------------------------------------------------


class DescribeVectorUpsertDimensionValidation:
    async def it_accepts_384_dimension_embedding(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=VECTOR_PAYLOAD)
        vector = await sdk.vectors.upsert(
            EMBEDDING_384, {"document": "text", "model": "BAAI/bge-small-en-v1.5"}
        )
        assert isinstance(vector, Vector)

    async def it_accepts_768_dimension_embedding(self, sdk, mock_httpx_client):
        payload = {**VECTOR_PAYLOAD, "embedding": EMBEDDING_768}
        mock_httpx_client.request.return_value = make_response(201, json_body=payload)
        vector = await sdk.vectors.upsert(EMBEDDING_768, {"document": "text", "model": "model"})
        assert isinstance(vector, Vector)

    async def it_accepts_1024_dimension_embedding(self, sdk, mock_httpx_client):
        payload = {**VECTOR_PAYLOAD, "embedding": EMBEDDING_1024}
        mock_httpx_client.request.return_value = make_response(201, json_body=payload)
        vector = await sdk.vectors.upsert(EMBEDDING_1024, {"document": "text", "model": "model"})
        assert isinstance(vector, Vector)

    async def it_accepts_1536_dimension_embedding(self, sdk, mock_httpx_client):
        payload = {**VECTOR_PAYLOAD, "embedding": EMBEDDING_1536}
        mock_httpx_client.request.return_value = make_response(201, json_body=payload)
        vector = await sdk.vectors.upsert(EMBEDDING_1536, {"document": "text", "model": "model"})
        assert isinstance(vector, Vector)

    async def it_raises_dimension_error_for_unsupported_size(self, sdk, mock_httpx_client):
        with pytest.raises(DimensionError) as exc_info:
            await sdk.vectors.upsert(EMBEDDING_INVALID, {"document": "text"})
        assert exc_info.value.actual == 512

    async def it_raises_dimension_error_before_making_network_call(self, sdk, mock_httpx_client):
        with pytest.raises(DimensionError):
            await sdk.vectors.upsert(EMBEDDING_INVALID, {"document": "text"})
        mock_httpx_client.request.assert_not_called()

    async def it_raises_dimension_error_for_empty_embedding(self, sdk, mock_httpx_client):
        with pytest.raises(DimensionError) as exc_info:
            await sdk.vectors.upsert([], {"document": "text"})
        assert exc_info.value.actual == 0

    async def it_includes_supported_dimensions_in_error_message(self, sdk, mock_httpx_client):
        with pytest.raises(DimensionError) as exc_info:
            await sdk.vectors.upsert([0.1] * 300, {"document": "text"})
        assert "384" in str(exc_info.value)


# ---------------------------------------------------------------------------
# describe: VectorOperations.upsert — happy path
# ---------------------------------------------------------------------------


class DescribeVectorUpsert:
    async def it_returns_vector_model_on_success(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=VECTOR_PAYLOAD)
        vector = await sdk.vectors.upsert(EMBEDDING_384, {"document": "text", "model": "m"})
        assert vector.id == "vec_abc1234567890123"
        assert vector.created is True

    async def it_posts_to_vectors_endpoint(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=VECTOR_PAYLOAD)
        await sdk.vectors.upsert(EMBEDDING_384, {"document": "text"})
        call = mock_httpx_client.request.call_args
        assert call.kwargs["method"] == "POST"
        assert "/vectors" in call.kwargs["url"]

    async def it_sends_embedding_and_metadata_in_payload(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=VECTOR_PAYLOAD)
        meta = {"document": "hello world", "model": "BAAI/bge-small-en-v1.5"}
        await sdk.vectors.upsert(EMBEDDING_384, meta)
        call = mock_httpx_client.request.call_args
        assert call.kwargs["json"]["metadata"] == meta
        assert len(call.kwargs["json"]["embedding"]) == 384

    async def it_includes_optional_vector_id_when_provided(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=VECTOR_PAYLOAD)
        await sdk.vectors.upsert(EMBEDDING_384, {"document": "d"}, vector_id="vec_custom")
        call = mock_httpx_client.request.call_args
        assert call.kwargs["json"]["vector_id"] == "vec_custom"

    async def it_omits_vector_id_key_when_not_provided(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=VECTOR_PAYLOAD)
        await sdk.vectors.upsert(EMBEDDING_384, {"document": "d"})
        call = mock_httpx_client.request.call_args
        assert "vector_id" not in call.kwargs["json"]


# ---------------------------------------------------------------------------
# describe: VectorOperations.search
# ---------------------------------------------------------------------------


class DescribeVectorSearch:
    async def it_returns_list_of_search_results(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            200, json_body=[VECTOR_SEARCH_RESULT]
        )
        results = await sdk.vectors.search("query text")
        assert len(results) == 1
        assert isinstance(results[0], VectorSearchResult)
        assert results[0].score == 0.87

    async def it_posts_query_to_search_endpoint(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[])
        await sdk.vectors.search("my query")
        call = mock_httpx_client.request.call_args
        assert "/vectors/search" in call.kwargs["url"]
        assert call.kwargs["json"]["query"] == "my query"

    async def it_includes_limit_in_payload(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[])
        await sdk.vectors.search("query", limit=20)
        call = mock_httpx_client.request.call_args
        assert call.kwargs["json"]["limit"] == 20

    async def it_defaults_limit_to_10(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[])
        await sdk.vectors.search("query")
        call = mock_httpx_client.request.call_args
        assert call.kwargs["json"]["limit"] == 10

    async def it_returns_results_from_wrapped_response(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            200, json_body={"results": [VECTOR_SEARCH_RESULT]}
        )
        results = await sdk.vectors.search("query")
        assert len(results) == 1

    async def it_returns_empty_list_when_no_matches(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[])
        results = await sdk.vectors.search("obscure query")
        assert results == []


# ---------------------------------------------------------------------------
# describe: VectorOperations.delete
# ---------------------------------------------------------------------------


class DescribeVectorDelete:
    async def it_sends_delete_request_to_vector_url(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(204, content=b"")
        await sdk.vectors.delete("vec_abc1234567890123")
        call = mock_httpx_client.request.call_args
        assert call.kwargs["method"] == "DELETE"
        assert "/vectors/vec_abc1234567890123" in call.kwargs["url"]

    async def it_returns_none_on_success(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(204, content=b"")
        result = await sdk.vectors.delete("vec_abc1234567890123")
        assert result is None

    async def it_raises_not_found_for_unknown_vector(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(404, text_body="Not found")
        with pytest.raises(NotFoundError):
            await sdk.vectors.delete("vec_missing")


# ---------------------------------------------------------------------------
# describe: DimensionError
# ---------------------------------------------------------------------------


class DescribeDimensionError:
    def it_stores_actual_dimension(self):
        err = DimensionError(512)
        assert err.actual == 512

    def it_includes_actual_in_message(self):
        err = DimensionError(512)
        assert "512" in str(err)

    def it_lists_supported_dimensions_in_message(self):
        err = DimensionError(512)
        for dim in (384, 768, 1024, 1536):
            assert str(dim) in str(err)

    def it_is_subclass_of_ainative_error(self):
        from ainative_agent.errors import AINativeError
        assert issubclass(DimensionError, AINativeError)
