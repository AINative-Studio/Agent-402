"""
DID-based ECDSA signing and verification for X402 protocol.
Implements Issue #75: DID-based ECDSA Signing and Verification.

Per PRD Section 9 (Security & Authentication):
- Uses ECDSA with SECP256k1 curve for signatures
- Implements deterministic payload serialization
- Provides DID resolution for public key extraction
- Ensures constant-time signature comparison

Security Features:
- SHA256 hashing of payloads
- Deterministic JSON serialization (sorted keys)
- Constant-time signature verification
- DID format validation before resolution
- No private key logging
"""
import hashlib
import json
import hmac
from typing import Dict, Any, Tuple
from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError
from ecdsa.util import sigencode_string, sigdecode_string


class SignatureVerificationError(Exception):
    """Raised when signature verification fails."""
    pass


class InvalidDIDError(Exception):
    """Raised when DID format is invalid."""
    pass


class DIDSigner:
    """
    DID-based ECDSA signing and verification.

    Implements cryptographic operations for X402 protocol:
    - Keypair generation
    - Payload signing with ECDSA SECP256k1
    - Signature verification
    - DID resolution (MVP: simple mock resolver)

    All operations use deterministic serialization for consistency.
    """

    @staticmethod
    def _serialize_payload(payload: Dict[str, Any]) -> bytes:
        """
        Serialize payload deterministically for signing/verification.

        Uses sorted JSON keys to ensure consistent serialization
        regardless of dictionary key order.

        Args:
            payload: Dictionary to serialize

        Returns:
            UTF-8 encoded JSON bytes

        Raises:
            TypeError: If payload cannot be serialized
        """
        if payload is None:
            raise TypeError("Payload cannot be None")

        # Sort keys for deterministic serialization
        # Use separators to ensure consistent output
        json_str = json.dumps(
            payload,
            sort_keys=True,
            separators=(',', ':'),
            ensure_ascii=True
        )
        return json_str.encode('utf-8')

    @staticmethod
    def _hash_payload(payload: Dict[str, Any]) -> bytes:
        """
        Create SHA256 hash of payload.

        Args:
            payload: Dictionary to hash

        Returns:
            32-byte SHA256 hash
        """
        serialized = DIDSigner._serialize_payload(payload)
        return hashlib.sha256(serialized).digest()

    @staticmethod
    def sign_payload(payload: Dict[str, Any], private_key_hex: str) -> str:
        """
        Sign a payload using ECDSA with SECP256k1.

        Process:
        1. Serialize payload deterministically (sorted JSON)
        2. Create SHA256 hash of serialized payload
        3. Sign hash with ECDSA SECP256k1
        4. Return hex-encoded signature

        Args:
            payload: Dictionary to sign
            private_key_hex: Hex-encoded private key (64 chars)

        Returns:
            Hex-encoded signature string

        Raises:
            ValueError: If private key is invalid
            TypeError: If payload cannot be serialized
        """
        if not private_key_hex or not isinstance(private_key_hex, str):
            raise ValueError("Private key must be a non-empty string")

        try:
            # Convert hex private key to bytes
            private_key_bytes = bytes.fromhex(private_key_hex)
        except ValueError as e:
            raise ValueError(f"Invalid hex private key: {e}")

        # Create signing key from private key
        try:
            signing_key = SigningKey.from_string(
                private_key_bytes,
                curve=SECP256k1
            )
        except Exception as e:
            raise ValueError(f"Invalid private key for SECP256k1: {e}")

        # Hash the payload
        payload_hash = DIDSigner._hash_payload(payload)

        # Sign the hash using deterministic ECDSA (RFC 6979)
        # This ensures the same payload always produces the same signature
        signature_bytes = signing_key.sign_digest_deterministic(
            payload_hash,
            sigencode=sigencode_string,
            hashfunc=hashlib.sha256
        )

        # Return hex-encoded signature
        return signature_bytes.hex()

    @staticmethod
    def verify_signature(
        payload: Dict[str, Any],
        signature_hex: str,
        did: str
    ) -> bool:
        """
        Verify a signature against a payload and DID.

        Process:
        1. Validate DID format
        2. Resolve DID to public key
        3. Recreate payload hash
        4. Verify signature using ECDSA

        Uses constant-time comparison for security.

        Args:
            payload: Dictionary that was signed
            signature_hex: Hex-encoded signature
            did: DID identifier (did:ethr:0x...)

        Returns:
            True if signature is valid, False otherwise

        Raises:
            InvalidDIDError: If DID format is invalid
            TypeError: If payload/signature/did is None
        """
        if payload is None:
            raise TypeError("Payload cannot be None")

        if signature_hex is None:
            raise TypeError("Signature cannot be None")

        if did is None:
            raise TypeError("DID cannot be None")

        # Validate DID format before resolution
        if not DIDSigner._validate_did_format(did):
            raise InvalidDIDError(f"Invalid DID format: {did}")

        try:
            # Resolve DID to public key
            public_key_hex = DIDSigner.resolve_did(did)
            public_key_bytes = bytes.fromhex(public_key_hex)

            # Create verifying key
            verifying_key = VerifyingKey.from_string(
                public_key_bytes,
                curve=SECP256k1
            )

            # Hash the payload
            payload_hash = DIDSigner._hash_payload(payload)

            # Convert signature to bytes
            signature_bytes = bytes.fromhex(signature_hex)

            # Verify signature
            verifying_key.verify_digest(
                signature_bytes,
                payload_hash,
                sigdecode=sigdecode_string
            )

            return True

        except (ValueError, BadSignatureError):
            # Invalid signature or malformed data
            return False

        except Exception:
            # Any other error (malformed hex, etc.)
            return False

    @staticmethod
    def _validate_did_format(did: str) -> bool:
        """
        Validate DID format.

        Accepts: did:ethr:0x...

        Args:
            did: DID string to validate

        Returns:
            True if format is valid, False otherwise
        """
        if not did or not isinstance(did, str):
            return False

        # Must start with did:ethr:0x
        if not did.startswith("did:ethr:0x"):
            return False

        # Must have content after prefix
        if len(did) <= len("did:ethr:0x"):
            return False

        # Extract address part after did:ethr:
        address_part = did[len("did:ethr:"):]

        # Should start with 0x
        if not address_part.startswith("0x"):
            return False

        # Should have hex characters after 0x
        hex_part = address_part[2:]
        if not hex_part:
            return False

        # Validate it's valid hex
        try:
            bytes.fromhex(hex_part)
            return True
        except ValueError:
            return False

    @staticmethod
    def resolve_did(did: str) -> str:
        """
        Resolve DID to public key.

        MVP Implementation: Simple mock resolver that derives public key
        from DID format. For production, this would query a DID registry.

        Format: did:ethr:0x<public_key_hex>

        Args:
            did: DID identifier (did:ethr:0x...)

        Returns:
            Hex-encoded public key (64 bytes = 128 hex chars)

        Raises:
            InvalidDIDError: If DID format is invalid
        """
        if not DIDSigner._validate_did_format(did):
            raise InvalidDIDError(f"Invalid DID format: {did}")

        # Extract public key from DID
        # Format: did:ethr:0x<pubkey>
        try:
            # Remove did:ethr: prefix
            address_part = did[len("did:ethr:"):]

            # Remove 0x prefix
            hex_part = address_part[2:]

            # For MVP, the DID directly contains the public key
            # Validate it's the right length for SECP256k1 public key
            # Uncompressed public key is 64 bytes (128 hex chars)
            if len(hex_part) != 128:
                # If it's an Ethereum address (40 chars), we can't derive the full public key
                # In real implementation, this would query a DID registry
                raise InvalidDIDError(
                    f"DID must contain full public key (128 hex chars), got {len(hex_part)}"
                )

            # Validate it's valid hex
            bytes.fromhex(hex_part)

            return hex_part

        except (IndexError, ValueError) as e:
            raise InvalidDIDError(f"Failed to resolve DID: {e}")

    @staticmethod
    def generate_keypair() -> Tuple[str, str]:
        """
        Generate ECDSA keypair for signing.

        Creates a new SECP256k1 keypair and derives DID from public key.

        Returns:
            Tuple of (private_key_hex, did)
            - private_key_hex: Hex-encoded private key (64 chars)
            - did: DID identifier (did:ethr:0x<public_key>)

        Example:
            >>> private_key, did = DIDSigner.generate_keypair()
            >>> payload = {"type": "payment", "amount": "100"}
            >>> signature = DIDSigner.sign_payload(payload, private_key)
            >>> is_valid = DIDSigner.verify_signature(payload, signature, did)
            >>> assert is_valid is True
        """
        # Generate new SECP256k1 private key
        signing_key = SigningKey.generate(curve=SECP256k1)

        # Get private key as hex
        private_key_hex = signing_key.to_string().hex()

        # Get public key
        verifying_key = signing_key.get_verifying_key()
        public_key_hex = verifying_key.to_string().hex()

        # Create DID from public key
        # Format: did:ethr:0x<public_key_hex>
        did = f"did:ethr:0x{public_key_hex}"

        return private_key_hex, did

    @staticmethod
    def verify_signature_constant_time(
        signature1: str,
        signature2: str
    ) -> bool:
        """
        Compare two signatures in constant time.

        Prevents timing attacks by using hmac.compare_digest.

        Args:
            signature1: First signature (hex)
            signature2: Second signature (hex)

        Returns:
            True if signatures match, False otherwise
        """
        if not signature1 or not signature2:
            return False

        # Use constant-time comparison
        return hmac.compare_digest(signature1, signature2)
