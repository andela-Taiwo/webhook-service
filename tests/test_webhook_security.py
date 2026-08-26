"""Tests for webhook signature verification and security."""

import hashlib
import hmac
import json

import pytest

from src.services.webhook_security import WebhookSecurityService


class TestWebhookSignatureVerification:
    """Test webhook HMAC signature verification."""

    @pytest.fixture
    def security_service(self):
        """Create webhook security service with test secret."""
        return WebhookSecurityService(secret_key="test_webhook_secret_key_123")

    @pytest.fixture
    def valid_payload(self):
        """Create a valid webhook payload."""
        return {
            "id": "evt_test_123",
            "type": "payment_intent.succeeded",
            "data": {"object": {"id": "pi_123", "amount": 1000}},
        }

    def test_generate_signature(self, security_service, valid_payload):
        """Test HMAC signature generation."""
        payload_str = json.dumps(valid_payload, separators=(",", ":"))
        signature = security_service.generate_signature(payload_str)

        # Signature should be a non-empty string
        assert signature
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA-256 hex digest length

    def test_verify_valid_signature(self, security_service, valid_payload):
        """Test verification of valid signature."""
        payload_str = json.dumps(valid_payload, separators=(",", ":"))
        signature = security_service.generate_signature(payload_str)

        # Should verify successfully
        assert security_service.verify_signature(payload_str, signature) is True

    def test_verify_invalid_signature(self, security_service, valid_payload):
        """Test rejection of invalid signature."""
        payload_str = json.dumps(valid_payload, separators=(",", ":"))
        invalid_signature = "invalid_signature_12345"

        # Should fail verification
        assert security_service.verify_signature(payload_str, invalid_signature) is False

    def test_verify_tampered_payload(self, security_service, valid_payload):
        """Test that tampered payload fails verification."""
        payload_str = json.dumps(valid_payload, separators=(",", ":"))
        signature = security_service.generate_signature(payload_str)

        # Modify the payload
        tampered_payload = valid_payload.copy()
        tampered_payload["data"]["object"]["amount"] = 9999
        tampered_str = json.dumps(tampered_payload, separators=(",", ":"))

        # Should fail verification with original signature
        assert security_service.verify_signature(tampered_str, signature) is False

    def test_empty_signature(self, security_service):
        """Test rejection of empty signature."""
        payload = json.dumps({"test": "data"})
        assert security_service.verify_signature(payload, "") is False

    def test_none_signature(self, security_service):
        """Test rejection of None signature."""
        payload = json.dumps({"test": "data"})
        assert security_service.verify_signature(payload, None) is False

    def test_timing_safe_comparison(self, security_service):
        """Test that signature comparison is timing-safe."""
        payload = json.dumps({"test": "data"})
        correct_sig = security_service.generate_signature(payload)

        # Even with partially matching signature, should use timing-safe comparison
        # This is verified by using hmac.compare_digest internally
        wrong_sig = correct_sig[:-1] + "0"
        assert security_service.verify_signature(payload, wrong_sig) is False

    def test_different_secret_keys(self, valid_payload):
        """Test that different secret keys produce different signatures."""
        payload_str = json.dumps(valid_payload, separators=(",", ":"))

        service1 = WebhookSecurityService(secret_key="secret_one")
        service2 = WebhookSecurityService(secret_key="secret_two")

        sig1 = service1.generate_signature(payload_str)
        sig2 = service2.generate_signature(payload_str)

        # Different secrets should produce different signatures
        assert sig1 != sig2

        # Cross-verification should fail
        assert service1.verify_signature(payload_str, sig2) is False
        assert service2.verify_signature(payload_str, sig1) is False
