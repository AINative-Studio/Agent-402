"""
Zero-human provisioning service.

Handles wallet-signature-based API key issuance and dynamic key management.
Keys are persisted in ZeroDB so they survive restarts and are queryable
by the auth middleware.

Refs AINative-Studio/Agent-402#363
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from eth_account import Account
from eth_account.messages import encode_defunct

from app.core.errors import APIError
from app.services.zerodb_client import get_zerodb_client

logger = logging.getLogger(__name__)

PROVISIONED_KEYS_TABLE = "provisioned_api_keys"


class InvalidSignatureError(APIError):
    def __init__(self, detail: str = "Wallet signature is invalid"):
        super().__init__(status_code=401, error_code="INVALID_SIGNATURE", detail=detail)


class ProvisionService:
    """Manages wallet-gated API key provisioning stored in ZeroDB."""

    def __init__(self, client=None):
        self._client = client

    def _get_client(self):
        return self._client or get_zerodb_client()

    # ------------------------------------------------------------------
    # Signature verification
    # ------------------------------------------------------------------

    def _recover_signer(self, message: str, signature: str) -> str:
        """Return the lowercased wallet address that signed *message*."""
        signable = encode_defunct(text=message)
        return Account.recover_message(signable, signature=signature).lower()

    def verify_wallet_ownership(
        self, wallet_address: str, message: str, signature: str
    ) -> bool:
        """Return True if *signature* proves ownership of *wallet_address*."""
        try:
            recovered = self._recover_signer(message, signature)
            return recovered == wallet_address.lower()
        except Exception as exc:
            logger.warning("Signature verification failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Key storage helpers
    # ------------------------------------------------------------------

    def _generate_api_key(self) -> str:
        return f"a402_{secrets.token_urlsafe(32)}"

    def _user_id_from_wallet(self, wallet_address: str) -> str:
        return "wa_" + hashlib.sha256(wallet_address.lower().encode()).hexdigest()[:16]

    async def _ensure_table(self):
        client = self._get_client()
        try:
            await client.create_table(
                PROVISIONED_KEYS_TABLE,
                {
                    "columns": [
                        {"name": "api_key", "type": "text", "unique": True},
                        {"name": "user_id", "type": "text"},
                        {"name": "wallet_address", "type": "text"},
                        {"name": "key_name", "type": "text"},
                        {"name": "created_at", "type": "text"},
                        {"name": "is_active", "type": "boolean"},
                    ]
                },
            )
        except Exception:
            # Table likely already exists — ignore
            pass

    def _unwrap_row(self, row: dict) -> dict:
        """Extract row_data from ZeroDB row envelope."""
        return row.get("row_data", row)

    async def _lookup_key(self, api_key: str) -> Optional[dict]:
        client = self._get_client()
        try:
            result = await client.query_rows(
                PROVISIONED_KEYS_TABLE,
                filter={"api_key": api_key, "is_active": True},
                limit=1,
            )
            rows = result.get("data", result) if isinstance(result, dict) else result
            return self._unwrap_row(rows[0]) if rows else None
        except Exception as exc:
            logger.error("lookup_key error: %s", exc)
            return None

    async def _lookup_by_wallet(self, wallet_address: str) -> Optional[dict]:
        client = self._get_client()
        try:
            result = await client.query_rows(
                PROVISIONED_KEYS_TABLE,
                filter={"wallet_address": wallet_address.lower(), "is_active": True},
                limit=1,
            )
            rows = result.get("data", result) if isinstance(result, dict) else result
            return self._unwrap_row(rows[0]) if rows else None
        except Exception as exc:
            logger.error("lookup_by_wallet error: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def provision(
        self, wallet_address: str, message: str, signature: str
    ) -> dict:
        """
        Verify wallet ownership and return (or create) an API key.

        Returns:
            { api_key, user_id, wallet_address, created_at, capabilities_url }
        """
        if not self.verify_wallet_ownership(wallet_address, message, signature):
            raise InvalidSignatureError()

        await self._ensure_table()

        wallet_lower = wallet_address.lower()
        existing = await self._lookup_by_wallet(wallet_lower)
        if existing:
            return {
                "api_key": existing["api_key"],
                "user_id": existing["user_id"],
                "wallet_address": wallet_lower,
                "created_at": existing["created_at"],
                "capabilities_url": "https://api.ainative.studio/agent402/v1/public/capabilities",
            }

        api_key = self._generate_api_key()
        user_id = self._user_id_from_wallet(wallet_lower)
        now = datetime.now(timezone.utc).isoformat()

        client = self._get_client()
        await client.insert_row(
            PROVISIONED_KEYS_TABLE,
            {
                "api_key": api_key,
                "user_id": user_id,
                "wallet_address": wallet_lower,
                "key_name": "provisioned",
                "created_at": now,
                "is_active": True,
            },
        )

        logger.info("Provisioned API key for wallet %s → user %s", wallet_lower, user_id)

        return {
            "api_key": api_key,
            "user_id": user_id,
            "wallet_address": wallet_lower,
            "created_at": now,
            "capabilities_url": "https://api.ainative.studio/agent402/v1/public/capabilities",
        }

    async def create_key(self, user_id: str, key_name: str = "default") -> dict:
        """
        Create an additional API key for an already-authenticated user.

        Returns:
            { api_key, key_id, user_id, key_name, created_at }
        """
        await self._ensure_table()

        api_key = self._generate_api_key()
        key_id = secrets.token_hex(8)
        now = datetime.now(timezone.utc).isoformat()

        client = self._get_client()
        await client.insert_row(
            PROVISIONED_KEYS_TABLE,
            {
                "api_key": api_key,
                "user_id": user_id,
                "wallet_address": "",
                "key_name": key_name,
                "created_at": now,
                "is_active": True,
            },
        )

        logger.info("Created additional API key for user %s (name=%s)", user_id, key_name)

        return {
            "api_key": api_key,
            "key_id": key_id,
            "user_id": user_id,
            "key_name": key_name,
            "created_at": now,
        }

    async def validate_dynamic_key(self, api_key: str) -> Optional[str]:
        """
        Return user_id if *api_key* is a valid dynamically-provisioned key,
        else None. Called by the auth middleware as a fallback.
        """
        row = await self._lookup_key(api_key)
        return row["user_id"] if row else None


# Singleton
_service: Optional[ProvisionService] = None


def get_provision_service() -> ProvisionService:
    global _service
    if _service is None:
        _service = ProvisionService()
    return _service
