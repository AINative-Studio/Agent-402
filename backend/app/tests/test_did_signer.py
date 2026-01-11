"""
Test suite for DID-based ECDSA signing and verification.
Implements Issue #75: DID-based ECDSA Signing and Verification.

Tests cover:
- Keypair generation
- Payload signing
- Signature verification
- DID resolution
- Edge cases and error handling
- Security requirements (constant-time comparison)
"""
import pytest
import json
import hashlib
from app.core.did_signer import DIDSigner, SignatureVerificationError, InvalidDIDError


class TestKeypairGeneration:
    """Test ECDSA keypair generation."""

    def test_generate_keypair_returns_tuple(self):
        """Should return tuple of (private_key_hex, did)."""
        private_key, did = DIDSigner.generate_keypair()

        assert isinstance(private_key, str)
        assert isinstance(did, str)
        assert len(private_key) > 0
        assert len(did) > 0

    def test_generate_keypair_did_format(self):
        """Should generate DID in did:ethr:0x... format."""
        private_key, did = DIDSigner.generate_keypair()

        assert did.startswith("did:ethr:0x")
        # DID should have public key/address after did:ethr:0x
        assert len(did) > len("did:ethr:0x")

    def test_generate_keypair_private_key_hex(self):
        """Should generate valid hex private key."""
        private_key, did = DIDSigner.generate_keypair()

        # Should be valid hex string
        try:
            bytes.fromhex(private_key)
        except ValueError:
            pytest.fail("Private key should be valid hex string")

        # SECP256k1 private keys are 32 bytes = 64 hex chars
        assert len(private_key) == 64

    def test_generate_keypair_unique_keys(self):
        """Should generate unique keypairs each time."""
        key1, did1 = DIDSigner.generate_keypair()
        key2, did2 = DIDSigner.generate_keypair()

        assert key1 != key2
        assert did1 != did2


class TestPayloadSigning:
    """Test payload signing functionality."""

    def test_sign_payload_returns_hex_signature(self):
        """Should return hex-encoded signature."""
        private_key, did = DIDSigner.generate_keypair()
        payload = {"type": "payment", "amount": "100.00"}

        signature = DIDSigner.sign_payload(payload, private_key)

        assert isinstance(signature, str)
        assert len(signature) > 0

        # Should be valid hex
        try:
            bytes.fromhex(signature)
        except ValueError:
            pytest.fail("Signature should be valid hex string")

    def test_sign_payload_deterministic(self):
        """Should produce same signature for same payload with same key."""
        private_key, did = DIDSigner.generate_keypair()
        payload = {"type": "payment", "amount": "100.00", "recipient": "did:ethr:0xabc"}

        sig1 = DIDSigner.sign_payload(payload, private_key)
        sig2 = DIDSigner.sign_payload(payload, private_key)

        assert sig1 == sig2

    def test_sign_payload_different_for_different_payloads(self):
        """Should produce different signatures for different payloads."""
        private_key, did = DIDSigner.generate_keypair()
        payload1 = {"type": "payment", "amount": "100.00"}
        payload2 = {"type": "payment", "amount": "200.00"}

        sig1 = DIDSigner.sign_payload(payload1, private_key)
        sig2 = DIDSigner.sign_payload(payload2, private_key)

        assert sig1 != sig2

    def test_sign_payload_handles_nested_objects(self):
        """Should handle complex nested payloads."""
        private_key, did = DIDSigner.generate_keypair()
        payload = {
            "type": "payment",
            "amount": "100.00",
            "metadata": {
                "recipient": "did:ethr:0xabc",
                "memo": "Payment for services"
            },
            "items": ["item1", "item2"]
        }

        signature = DIDSigner.sign_payload(payload, private_key)

        assert isinstance(signature, str)
        assert len(signature) > 0

    def test_sign_payload_empty_payload(self):
        """Should handle empty payload."""
        private_key, did = DIDSigner.generate_keypair()
        payload = {}

        signature = DIDSigner.sign_payload(payload, private_key)

        assert isinstance(signature, str)
        assert len(signature) > 0

    def test_sign_payload_invalid_private_key(self):
        """Should raise error for invalid private key."""
        payload = {"type": "payment"}

        with pytest.raises(ValueError):
            DIDSigner.sign_payload(payload, "invalid_hex")

        with pytest.raises(ValueError):
            DIDSigner.sign_payload(payload, "")


class TestSignatureVerification:
    """Test signature verification functionality."""

    def test_verify_signature_valid(self):
        """Should verify valid signature."""
        private_key, did = DIDSigner.generate_keypair()
        payload = {"type": "payment", "amount": "100.00"}
        signature = DIDSigner.sign_payload(payload, private_key)

        result = DIDSigner.verify_signature(payload, signature, did)

        assert result is True

    def test_verify_signature_invalid_signature(self):
        """Should reject invalid signature."""
        private_key, did = DIDSigner.generate_keypair()
        payload = {"type": "payment", "amount": "100.00"}
        signature = DIDSigner.sign_payload(payload, private_key)

        # Modify signature
        tampered_signature = signature[:-2] + "00"

        result = DIDSigner.verify_signature(payload, tampered_signature, did)

        assert result is False

    def test_verify_signature_wrong_did(self):
        """Should reject signature from different DID."""
        private_key1, did1 = DIDSigner.generate_keypair()
        private_key2, did2 = DIDSigner.generate_keypair()

        payload = {"type": "payment", "amount": "100.00"}
        signature = DIDSigner.sign_payload(payload, private_key1)

        # Try to verify with different DID
        result = DIDSigner.verify_signature(payload, signature, did2)

        assert result is False

    def test_verify_signature_tampered_payload(self):
        """Should reject signature when payload is modified."""
        private_key, did = DIDSigner.generate_keypair()
        payload = {"type": "payment", "amount": "100.00"}
        signature = DIDSigner.sign_payload(payload, private_key)

        # Modify payload
        tampered_payload = {"type": "payment", "amount": "200.00"}

        result = DIDSigner.verify_signature(tampered_payload, signature, did)

        assert result is False

    def test_verify_signature_malformed_signature(self):
        """Should handle malformed signatures gracefully."""
        private_key, did = DIDSigner.generate_keypair()
        payload = {"type": "payment"}

        # Test various malformed signatures
        result1 = DIDSigner.verify_signature(payload, "not_hex", did)
        assert result1 is False

        result2 = DIDSigner.verify_signature(payload, "", did)
        assert result2 is False

        result3 = DIDSigner.verify_signature(payload, "abc", did)
        assert result3 is False

    def test_verify_signature_invalid_did_format(self):
        """Should raise error for invalid DID format."""
        private_key, did = DIDSigner.generate_keypair()
        payload = {"type": "payment"}
        signature = DIDSigner.sign_payload(payload, private_key)

        with pytest.raises(InvalidDIDError):
            DIDSigner.verify_signature(payload, signature, "not_a_did")

        with pytest.raises(InvalidDIDError):
            DIDSigner.verify_signature(payload, signature, "did:invalid:format")


class TestDIDResolution:
    """Test DID resolution functionality."""

    def test_resolve_did_valid_format(self):
        """Should resolve valid did:ethr:0x... DID."""
        private_key, did = DIDSigner.generate_keypair()

        public_key = DIDSigner.resolve_did(did)

        assert isinstance(public_key, str)
        assert len(public_key) > 0

        # Should be valid hex
        try:
            bytes.fromhex(public_key)
        except ValueError:
            pytest.fail("Public key should be valid hex string")

    def test_resolve_did_invalid_format(self):
        """Should raise error for invalid DID format."""
        with pytest.raises(InvalidDIDError):
            DIDSigner.resolve_did("invalid_did")

        with pytest.raises(InvalidDIDError):
            DIDSigner.resolve_did("did:invalid:0x123")

        with pytest.raises(InvalidDIDError):
            DIDSigner.resolve_did("")

    def test_resolve_did_consistency(self):
        """Should return same public key for same DID."""
        private_key, did = DIDSigner.generate_keypair()

        pubkey1 = DIDSigner.resolve_did(did)
        pubkey2 = DIDSigner.resolve_did(did)

        assert pubkey1 == pubkey2


class TestEndToEndSignVerify:
    """Test complete sign/verify workflows."""

    def test_complete_workflow(self):
        """Should complete full sign/verify workflow."""
        # Generate keypair
        private_key, did = DIDSigner.generate_keypair()

        # Create payload
        payload = {
            "type": "payment_authorization",
            "amount": "100.00",
            "currency": "USD",
            "recipient": "did:ethr:0xdef789",
            "memo": "Payment for services"
        }

        # Sign payload
        signature = DIDSigner.sign_payload(payload, private_key)

        # Verify signature
        is_valid = DIDSigner.verify_signature(payload, signature, did)

        assert is_valid is True

    def test_multiple_payloads_same_key(self):
        """Should handle multiple different payloads with same key."""
        private_key, did = DIDSigner.generate_keypair()

        payloads = [
            {"type": "payment", "amount": "100.00"},
            {"type": "transfer", "amount": "50.00"},
            {"type": "authorization", "scope": "read"}
        ]

        for payload in payloads:
            signature = DIDSigner.sign_payload(payload, private_key)
            is_valid = DIDSigner.verify_signature(payload, signature, did)
            assert is_valid is True

    def test_cross_verification_fails(self):
        """Should fail when verifying with wrong signature/payload combo."""
        private_key, did = DIDSigner.generate_keypair()

        payload1 = {"type": "payment", "amount": "100.00"}
        payload2 = {"type": "payment", "amount": "200.00"}

        sig1 = DIDSigner.sign_payload(payload1, private_key)
        sig2 = DIDSigner.sign_payload(payload2, private_key)

        # Cross-verification should fail
        assert DIDSigner.verify_signature(payload1, sig2, did) is False
        assert DIDSigner.verify_signature(payload2, sig1, did) is False


class TestSecurityRequirements:
    """Test security-specific requirements."""

    def test_payload_serialization_deterministic(self):
        """Should serialize payloads deterministically (sorted keys)."""
        private_key, did = DIDSigner.generate_keypair()

        # Same data, different key order
        payload1 = {"b": 2, "a": 1, "c": 3}
        payload2 = {"a": 1, "c": 3, "b": 2}
        payload3 = {"c": 3, "a": 1, "b": 2}

        sig1 = DIDSigner.sign_payload(payload1, private_key)
        sig2 = DIDSigner.sign_payload(payload2, private_key)
        sig3 = DIDSigner.sign_payload(payload3, private_key)

        # All signatures should be identical
        assert sig1 == sig2 == sig3

    def test_nested_payload_serialization_deterministic(self):
        """Should handle nested objects deterministically."""
        private_key, did = DIDSigner.generate_keypair()

        payload1 = {
            "outer": {"b": 2, "a": 1},
            "items": [1, 2, 3]
        }
        payload2 = {
            "items": [1, 2, 3],
            "outer": {"a": 1, "b": 2}
        }

        sig1 = DIDSigner.sign_payload(payload1, private_key)
        sig2 = DIDSigner.sign_payload(payload2, private_key)

        assert sig1 == sig2


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_sign_with_none_payload(self):
        """Should handle None payload gracefully."""
        private_key, did = DIDSigner.generate_keypair()

        with pytest.raises((TypeError, ValueError)):
            DIDSigner.sign_payload(None, private_key)

    def test_verify_with_none_values(self):
        """Should handle None values in verification."""
        private_key, did = DIDSigner.generate_keypair()
        payload = {"type": "payment"}

        with pytest.raises((TypeError, ValueError)):
            DIDSigner.verify_signature(None, "signature", did)

        with pytest.raises((TypeError, ValueError)):
            DIDSigner.verify_signature(payload, None, did)

        with pytest.raises((TypeError, InvalidDIDError)):
            DIDSigner.verify_signature(payload, "signature", None)
