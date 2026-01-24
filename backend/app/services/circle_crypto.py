"""
Circle API Cryptographic Operations.
Handles entity secret encryption for Circle Developer-Controlled Wallets API.

The entity secret ciphertext is required for all mutating API calls:
- Create wallet set
- Create wallets
- Create transfers
- Execute contract transactions

This module provides:
1. Fetching Circle's public key from their API
2. RSA-OAEP encryption of the entity secret
3. Base64 encoding for API transmission
4. Public key caching for performance

Security Notes:
- Entity secret is a 32-byte value (64 hex characters)
- Circle mandates unique ciphertext for each API request
- Uses RSA-OAEP with SHA-256 padding
"""
import base64
import logging
import os
import time
from typing import Optional, Tuple

import httpx
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256

logger = logging.getLogger(__name__)

# Cache for Circle's public key
_public_key_cache: dict = {
    "key": None,
    "key_id": None,
    "fetched_at": 0
}

# Cache TTL in seconds (1 hour)
PUBLIC_KEY_CACHE_TTL = 3600


class CircleCryptoError(Exception):
    """Raised when cryptographic operations fail."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        self.message = message
        self.cause = cause
        super().__init__(message)


async def fetch_public_key(
    api_key: str,
    base_url: str = "https://api.circle.com"
) -> Tuple[str, str]:
    """
    Fetch Circle's RSA public key from the API.

    Args:
        api_key: Circle API key for authentication
        base_url: Circle API base URL

    Returns:
        Tuple of (public_key_pem, key_id)

    Raises:
        CircleCryptoError: If fetching the public key fails
    """
    global _public_key_cache

    # Check cache first
    current_time = time.time()
    if (
        _public_key_cache["key"] is not None
        and (current_time - _public_key_cache["fetched_at"]) < PUBLIC_KEY_CACHE_TTL
    ):
        logger.debug("Using cached Circle public key")
        return _public_key_cache["key"], _public_key_cache["key_id"]

    # Fetch from API
    url = f"{base_url}/v1/w3s/config/entity/publicKey"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )

            if response.status_code != 200:
                error_msg = f"Failed to fetch public key: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('message', '')}"
                except Exception:
                    pass
                raise CircleCryptoError(error_msg)

            data = response.json()
            public_key = data.get("data", {}).get("publicKey")
            key_id = data.get("data", {}).get("keyId")

            if not public_key:
                raise CircleCryptoError("No public key in API response")

            # Update cache
            _public_key_cache["key"] = public_key
            _public_key_cache["key_id"] = key_id
            _public_key_cache["fetched_at"] = current_time

            logger.info("Successfully fetched Circle public key")
            return public_key, key_id

    except httpx.RequestError as e:
        raise CircleCryptoError(f"Network error fetching public key: {str(e)}", e)
    except Exception as e:
        if isinstance(e, CircleCryptoError):
            raise
        raise CircleCryptoError(f"Unexpected error fetching public key: {str(e)}", e)


def encrypt_entity_secret(
    entity_secret_hex: str,
    public_key_pem: str
) -> str:
    """
    Encrypt the entity secret using Circle's RSA public key.

    The encryption uses RSA-OAEP with SHA-256 padding.
    Each call generates a unique ciphertext due to OAEP padding randomness.

    Args:
        entity_secret_hex: 32-byte entity secret as hex string (64 characters)
        public_key_pem: Circle's RSA public key in PEM format

    Returns:
        Base64-encoded ciphertext string

    Raises:
        CircleCryptoError: If encryption fails or inputs are invalid
    """
    # Validate entity secret
    if not entity_secret_hex or len(entity_secret_hex) != 64:
        raise CircleCryptoError(
            f"Entity secret must be 64 hex characters (32 bytes), got {len(entity_secret_hex) if entity_secret_hex else 0}"
        )

    try:
        # Convert hex to bytes
        entity_secret_bytes = bytes.fromhex(entity_secret_hex)
    except ValueError as e:
        raise CircleCryptoError(f"Invalid hex string for entity secret: {str(e)}", e)

    try:
        # Load the RSA public key
        rsa_key = RSA.import_key(public_key_pem)

        # Create OAEP cipher with SHA-256
        cipher = PKCS1_OAEP.new(rsa_key, hashAlgo=SHA256)

        # Encrypt the entity secret
        ciphertext = cipher.encrypt(entity_secret_bytes)

        # Base64 encode
        encoded = base64.b64encode(ciphertext).decode('utf-8')

        logger.debug("Successfully encrypted entity secret")
        return encoded

    except Exception as e:
        raise CircleCryptoError(f"Failed to encrypt entity secret: {str(e)}", e)


async def generate_entity_secret_ciphertext(
    entity_secret_hex: str,
    api_key: str,
    base_url: str = "https://api.circle.com"
) -> str:
    """
    Generate entity secret ciphertext for Circle API requests.

    This is the main function to use for generating the entitySecretCiphertext
    parameter required by Circle's mutating API calls.

    Each call generates a fresh ciphertext (as required by Circle's API)
    even for the same entity secret, due to OAEP padding randomness.

    Args:
        entity_secret_hex: 32-byte entity secret as hex string
        api_key: Circle API key
        base_url: Circle API base URL

    Returns:
        Base64-encoded entity secret ciphertext

    Raises:
        CircleCryptoError: If ciphertext generation fails
    """
    # Fetch the public key (may use cache)
    public_key_pem, _ = await fetch_public_key(api_key, base_url)

    # Encrypt the entity secret
    ciphertext = encrypt_entity_secret(entity_secret_hex, public_key_pem)

    return ciphertext


def generate_entity_secret() -> str:
    """
    Generate a new random 32-byte entity secret.

    Returns:
        Hex-encoded 32-byte random value (64 characters)
    """
    return os.urandom(32).hex()


def clear_public_key_cache() -> None:
    """
    Clear the public key cache.

    Useful for testing or when key rotation is detected.
    """
    global _public_key_cache
    _public_key_cache = {
        "key": None,
        "key_id": None,
        "fetched_at": 0
    }
    logger.debug("Cleared Circle public key cache")
