"""Webhook security service for signature verification."""

import hmac
import hashlib
from typing import Optional


class WebhookSecurityService:
    """
    Service for webhook signature verification using HMAC-SHA256.

    This ensures that webhooks are:
    1. From a trusted source (only sender with secret key can generate valid signature)
    2. Not tampered with (any modification invalidates signature)
    3. Protected against timing attacks (uses constant-time comparison)
    """

    def __init__(self, secret_key: str):
        """
        Initialize security service with secret key.

        Args:
            secret_key: Secret key shared with webhook provider
        """
        if not secret_key:
            raise ValueError("Secret key cannot be empty")
        self.secret_key = secret_key.encode("utf-8")

    def generate_signature(self, payload: str) -> str:
        """
        Generate HMAC-SHA256 signature for payload.

        Args:
            payload: String representation of webhook payload

        Returns:
            Hexadecimal signature string
        """
        signature = hmac.new(
            key=self.secret_key, msg=payload.encode("utf-8"), digestmod=hashlib.sha256
        )
        return signature.hexdigest()

    def verify_signature(self, payload: str, provided_signature: Optional[str]) -> bool:
        """
        Verify webhook signature using timing-safe comparison.

        Args:
            payload: String representation of webhook payload
            provided_signature: Signature provided in webhook headers

        Returns:
            True if signature is valid, False otherwise
        """
        if not provided_signature:
            return False

        expected_signature = self.generate_signature(payload)

        # Use timing-safe comparison to prevent timing attacks
        return hmac.compare_digest(expected_signature, provided_signature)
