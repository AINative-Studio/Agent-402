#!/usr/bin/env python3
"""
Example usage of DID-based ECDSA signing for X402 requests.
Demonstrates Issue #75 implementation.

This example shows how to:
1. Generate a DID keypair
2. Sign an X402 payment payload
3. Verify the signature
4. Create an X402 request via API
"""
import requests
import json
from app.core.did_signer import DIDSigner


def main():
    """Demonstrate DID signing and X402 request creation."""

    print("=" * 60)
    print("DID-based ECDSA Signing Example")
    print("Issue #75: X402 Request Signing and Verification")
    print("=" * 60)
    print()

    # Step 1: Generate keypair
    print("Step 1: Generate ECDSA keypair")
    print("-" * 60)
    private_key, did = DIDSigner.generate_keypair()
    print(f"Private Key: {private_key}")
    print(f"DID: {did}")
    print()

    # Step 2: Create payment payload
    print("Step 2: Create X402 payment payload")
    print("-" * 60)
    payload = {
        "type": "payment_authorization",
        "amount": "150.00",
        "currency": "USD",
        "recipient": "did:ethr:0xabc123def456",
        "memo": "Payment for consulting services Q1 2026",
        "timestamp": "2026-01-11T12:00:00Z"
    }
    print(json.dumps(payload, indent=2))
    print()

    # Step 3: Sign the payload
    print("Step 3: Sign payload with ECDSA (SECP256k1)")
    print("-" * 60)
    signature = DIDSigner.sign_payload(payload, private_key)
    print(f"Signature: {signature}")
    print(f"Signature length: {len(signature)} chars")
    print()

    # Step 4: Verify signature locally
    print("Step 4: Verify signature locally")
    print("-" * 60)
    is_valid = DIDSigner.verify_signature(payload, signature, did)
    print(f"Signature valid: {is_valid}")
    print()

    # Step 5: Demonstrate deterministic signing
    print("Step 5: Demonstrate deterministic signing")
    print("-" * 60)
    signature2 = DIDSigner.sign_payload(payload, private_key)
    print(f"Second signature: {signature2}")
    print(f"Signatures match: {signature == signature2}")
    print()

    # Step 6: Create X402 request
    print("Step 6: Create X402 request via API")
    print("-" * 60)

    # Example API request (commented out - requires running server)
    api_url = "http://localhost:8000/v1/public/test_project_123/x402-requests"
    api_key = "demo_key_user1_abc123"

    request_data = {
        "agent_id": did,
        "task_id": "consulting_payment_q1",
        "run_id": "run_2026_01_11_example",
        "request_payload": payload,
        "signature": signature,
        "status": "PENDING",
        "metadata": {
            "department": "consulting",
            "quarter": "Q1-2026"
        }
    }

    print("API Request:")
    print(f"POST {api_url}")
    print(f"Headers: X-API-Key: {api_key}")
    print(f"Body: {json.dumps(request_data, indent=2)}")
    print()

    print("To execute this request, run:")
    print(f"curl -X POST '{api_url}' \\")
    print(f"  -H 'X-API-Key: {api_key}' \\")
    print(f"  -H 'Content-Type: application/json' \\")
    print(f"  -d '{json.dumps(request_data)}'")
    print()

    # Uncomment to actually make the request (requires running server)
    # try:
    #     response = requests.post(
    #         api_url,
    #         headers={
    #             "X-API-Key": api_key,
    #             "Content-Type": "application/json"
    #         },
    #         json=request_data
    #     )
    #     print(f"Response Status: {response.status_code}")
    #     print(f"Response Body: {json.dumps(response.json(), indent=2)}")
    # except Exception as e:
    #     print(f"Error making request: {e}")
    #     print("Make sure the server is running on localhost:8000")

    print("=" * 60)
    print("Example complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
