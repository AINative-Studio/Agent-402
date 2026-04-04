"""
File upload/download operations for ainative-agent SDK.

Built by AINative Dev Team.
"""
from __future__ import annotations

from typing import Any

from .client import AsyncHTTPClient
from .types import FileRecord


class FileOperations:
    """
    File storage operations: upload, download, list.
    """

    def __init__(self, client: AsyncHTTPClient) -> None:
        self._client = client

    async def upload(
        self,
        file: bytes,
        filename: str = "upload",
        content_type: str = "application/octet-stream",
        **metadata: Any,
    ) -> FileRecord:
        """
        Upload a file.

        Args:
            file: Raw file bytes.
            filename: Original filename hint.
            content_type: MIME type of the file.
            **metadata: Optional key-value metadata attached to the file.

        Returns:
            The created FileRecord.
        """
        headers = {
            "Content-Type": content_type,
            "X-Filename": filename,
        }
        if metadata:
            import json
            headers["X-Metadata"] = json.dumps(metadata)

        data = await self._client.post(
            "/files",
            content=file,
            headers=headers,
        )
        return FileRecord.model_validate(data)

    async def download(self, file_id: str) -> bytes:
        """
        Download a file by ID.

        Args:
            file_id: The file's unique identifier.

        Returns:
            Raw file bytes.

        Raises:
            NotFoundError: When the file does not exist.
        """
        raw = await self._client.get(f"/files/{file_id}/download")
        if isinstance(raw, bytes):
            return raw
        # If the server returned JSON with a content field, decode it
        if isinstance(raw, dict) and "content" in raw:
            content = raw["content"]
            if isinstance(content, str):
                import base64
                return base64.b64decode(content)
            if isinstance(content, bytes):
                return content
        raise ValueError(f"Unexpected response format for file download: {type(raw)}")

    async def list(self, **params: Any) -> list[FileRecord]:
        """
        List files, optionally filtered.

        Args:
            **params: Optional query parameters (limit, offset, …).

        Returns:
            List of FileRecord objects.
        """
        data = await self._client.get("/files", params=params or None)
        if isinstance(data, list):
            return [FileRecord.model_validate(item) for item in data]
        items = data.get("files", data.get("items", data.get("data", [])))
        return [FileRecord.model_validate(item) for item in items]
