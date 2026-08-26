#!/usr/bin/env python3
"""
Generate webhook signature for testing.

This script helps you:
1. Generate HMAC-SHA256 signatures for webhook payloads
2. Test webhook endpoints with proper signatures
3. Understand the signature generation process

Usage:
    python generate_key.py                          # Use default payload
    python generate_key.py '{"id": "evt_123", ...}' # Use custom payload
"""

import hashlib
import hmac
import json
import os
import sys


def generate_signature(payload_dict: dict, secret_key: str) -> tuple[str, str]:
    """
    Generate HMAC-SHA256 signature for a webhook payload.

    Args:
        payload_dict: Dictionary payload to sign
        secret_key: Secret key for HMAC

    Returns:
        Tuple of (payload_string, signature)
    """
    # Convert to JSON string (no whitespace, sorted keys for consistency)
    payload_str = json.dumps(payload_dict, separators=(",", ":"), sort_keys=True)

    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        key=secret_key.encode("utf-8"),
        msg=payload_str.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()

    return payload_str, signature


def print_curl_command(url: str, payload_str: str, signature: str) -> None:
    """Print a curl command for testing the webhook."""
    print("\n" + "=" * 80)
    print("CURL COMMAND FOR TESTING:")
    print("=" * 80)
    print(f"""
curl -X POST {url} \\
  -H "Content-Type: application/json" \\
  -H "X-Webhook-Signature: {signature}" \\
  -d '{payload_str}'
""")


def main():
    # Get secret key from environment or use default
    secret_key = os.getenv("WEBHOOK_SECRET_KEY", "test_secret_key_7272")

    # Sample payloads for different event types
    sample_payloads = {
        "payment_intent.succeeded": {
            "id": "evt_payment_1234567890",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "id": "pi_1234567890",
                    "amount": 5000,  # $50.00 in cents
                    "currency": "usd",
                    "customer_email": "customer@example.com",
                    "payment_method": "card",
                }
            },
        },
        "invoice.created": {
            "id": "evt_invoice_1234567890",
            "type": "invoice.created",
            "data": {
                "object": {
                    "id": "in_1234567890",
                    "invoice_number": "INV-2024-001",
                    "customer_email": "customer@example.com",
                    "amount_due": 10000,  # $100.00 in cents
                    "due_date": 1735689600,  # Unix timestamp
                }
            },
        },
        "charge.refunded": {
            "id": "evt_refund_1234567890",
            "type": "charge.refunded",
            "data": {
                "object": {
                    "id": "ch_1234567890",
                    "amount": 2500,  # $25.00 in cents
                    "customer_email": "customer@example.com",
                    "refund_reason": "requested_by_customer",
                }
            },
        },
        "customer.subscription.created": {
            "id": "evt_subscription_1234567890",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_1234567890",
                    "customer_email": "customer@example.com",
                    "plan": {"amount": 999},  # $9.99 in cents per month
                }
            },
        },
    }

    # Use custom payload if provided as argument, otherwise use default
    if len(sys.argv) > 1:
        try:
            payload = json.loads(sys.argv[1])
            event_type = "custom"
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON provided: {e}")
            sys.exit(1)
    else:
        # Default to payment event
        event_type = "payment_intent.succeeded"
        payload = sample_payloads[event_type]

    # Generate signature
    payload_str, signature = generate_signature(payload, secret_key)

    # Print results
    print("=" * 80)
    print("WEBHOOK SIGNATURE GENERATOR")
    print("=" * 80)
    print(f"\nEvent Type: {event_type}")
    print(f"Secret Key: {secret_key}")
    print(f"\nPayload (JSON):\n{json.dumps(payload, indent=2)}")
    print(f"\nPayload (String - used for signature):\n{payload_str}")
    print(f"\nSignature (HMAC-SHA256):\n{signature}")
    print(f"\nHeader:\nX-Webhook-Signature: {signature}")

    # Print curl command for local testing
    webhook_url = os.getenv("WEBHOOK_URL", "http://localhost:8000/api/v1/webhooks")
    print_curl_command(webhook_url, payload_str, signature)

    # Print all sample payloads if no custom payload
    if len(sys.argv) == 1:
        print("\n" + "=" * 80)
        print("OTHER SAMPLE EVENTS:")
        print("=" * 80)
        for event_name, event_payload in sample_payloads.items():
            if event_name != event_type:
                _, sig = generate_signature(event_payload, secret_key)
                print(f"\n{event_name}:")
                print(f"  Signature: {sig}")

    print("\n" + "=" * 80)
    print("POSTMAN TESTING INSTRUCTIONS:")
    print("=" * 80)
    print("""
⚠️  IMPORTANT: Postman's JSON editor reformats JSON, breaking signatures!

To test in Postman:
1. Method: POST
2. URL: http://localhost:8000/api/v1/webhooks
3. Headers:
   - Content-Type: application/json
   - X-Webhook-Signature: """ + signature + """
4. Body:
   - Select "raw" (NOT the JSON option)
   - Select "Text" from the dropdown (NOT JSON)
   - Copy the EXACT payload string below (no modifications):

COPY THIS EXACT STRING TO POSTMAN BODY:
""" + payload_str + """

5. Click Send

✅ The curl command above works because it sends the exact string.
❌ Don't use Postman's JSON editor - it adds whitespace and breaks signatures.
""")

    print("\n" + "=" * 80)
    print("NOTES:")
    print("=" * 80)
    print("""
1. The signature is generated from the JSON string representation
2. JSON is serialized with no whitespace and sorted keys
3. Both client and server must use the EXACT same string
4. Make sure WEBHOOK_SECRET_KEY environment variable matches on both sides
5. The signature header name is: X-Webhook-Signature
6. For Postman testing, see postman_guide.md for detailed instructions
""")


if __name__ == "__main__":
    main()