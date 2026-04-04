"""
Tests for ainative_agent.files — FileOperations.

Describes: upload, download, and list operations.

Built by AINative Dev Team.
"""
from __future__ import annotations

import base64

import pytest

from ainative_agent.errors import NotFoundError
from ainative_agent.types import FileRecord
from tests.conftest import make_response

# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

FILE_PAYLOAD = {
    "id": "file_abc1234567890",
    "filename": "data.txt",
    "size": 12,
    "content_type": "text/plain",
    "url": "https://storage.example.com/files/file_abc1234567890",
    "metadata": {},
    "created_at": "2024-01-01T00:00:00Z",
}

FILE_BYTES = b"hello world\n"


# ---------------------------------------------------------------------------
# describe: FileOperations.upload
# ---------------------------------------------------------------------------


class DescribeFileUpload:
    async def it_returns_file_record_on_success(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=FILE_PAYLOAD)
        record = await sdk.files.upload(FILE_BYTES, filename="data.txt")
        assert isinstance(record, FileRecord)
        assert record.id == "file_abc1234567890"
        assert record.filename == "data.txt"

    async def it_posts_to_files_endpoint(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=FILE_PAYLOAD)
        await sdk.files.upload(FILE_BYTES)
        call = mock_httpx_client.request.call_args
        assert call.kwargs["method"] == "POST"
        assert "/files" in call.kwargs["url"]

    async def it_sends_raw_bytes_as_body(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=FILE_PAYLOAD)
        await sdk.files.upload(FILE_BYTES, filename="data.txt")
        call = mock_httpx_client.request.call_args
        assert call.kwargs["content"] == FILE_BYTES

    async def it_sets_x_filename_header(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=FILE_PAYLOAD)
        await sdk.files.upload(FILE_BYTES, filename="report.csv")
        call = mock_httpx_client.request.call_args
        headers = call.kwargs["headers"]
        assert headers["X-Filename"] == "report.csv"

    async def it_sets_content_type_header(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=FILE_PAYLOAD)
        await sdk.files.upload(FILE_BYTES, content_type="text/plain")
        call = mock_httpx_client.request.call_args
        headers = call.kwargs["headers"]
        assert headers["Content-Type"] == "text/plain"

    async def it_defaults_content_type_to_octet_stream(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(201, json_body=FILE_PAYLOAD)
        await sdk.files.upload(FILE_BYTES)
        call = mock_httpx_client.request.call_args
        assert call.kwargs["headers"]["Content-Type"] == "application/octet-stream"

    async def it_raises_auth_error_on_401(self, sdk, mock_httpx_client):
        from ainative_agent.errors import AuthError
        mock_httpx_client.request.return_value = make_response(401, text_body="Unauthorized")
        with pytest.raises(AuthError):
            await sdk.files.upload(FILE_BYTES)


# ---------------------------------------------------------------------------
# describe: FileOperations.download
# ---------------------------------------------------------------------------


class DescribeFileDownload:
    async def it_returns_bytes_on_success(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, content=FILE_BYTES)
        content = await sdk.files.download("file_abc1234567890")
        assert content == FILE_BYTES

    async def it_requests_download_url(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, content=FILE_BYTES)
        await sdk.files.download("file_abc1234567890")
        call = mock_httpx_client.request.call_args
        assert "/files/file_abc1234567890/download" in call.kwargs["url"]

    async def it_raises_not_found_for_unknown_file(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(404, text_body="Not found")
        with pytest.raises(NotFoundError):
            await sdk.files.download("file_missing")

    async def it_decodes_base64_when_response_is_json_with_content_field(
        self, sdk, mock_httpx_client
    ):
        encoded = base64.b64encode(FILE_BYTES).decode()
        mock_httpx_client.request.return_value = make_response(
            200, json_body={"content": encoded}
        )
        content = await sdk.files.download("file_abc1234567890")
        assert content == FILE_BYTES


# ---------------------------------------------------------------------------
# describe: FileOperations.list
# ---------------------------------------------------------------------------


class DescribeFileList:
    async def it_returns_list_of_file_records(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[FILE_PAYLOAD])
        files = await sdk.files.list()
        assert len(files) == 1
        assert isinstance(files[0], FileRecord)

    async def it_returns_empty_list_when_no_files(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[])
        files = await sdk.files.list()
        assert files == []

    async def it_passes_query_params(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[])
        await sdk.files.list(limit=20, offset=10)
        call = mock_httpx_client.request.call_args
        assert call.kwargs["params"]["limit"] == 20
        assert call.kwargs["params"]["offset"] == 10

    async def it_returns_files_from_wrapped_response(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(
            200, json_body={"files": [FILE_PAYLOAD]}
        )
        files = await sdk.files.list()
        assert len(files) == 1

    async def it_does_not_send_params_when_no_filters(self, sdk, mock_httpx_client):
        mock_httpx_client.request.return_value = make_response(200, json_body=[])
        await sdk.files.list()
        call = mock_httpx_client.request.call_args
        assert call.kwargs["params"] is None
