import hmac
import hashlib
from typing import Optional


class MissingSecretError(Exception):
    """Raised when the webhook secret is not configured in the application."""
    pass


class GitHubWebhookVerifier:
    """
    Utility class for verifying GitHub webhook payloads using HMAC SHA-256.
    
    This class is framework-independent and does not rely on FastAPI or any
    specific web framework, allowing for flexible adoption across different
    API layers. It guarantees secure signature comparison using constant-time
    string comparisons to prevent timing attacks.
    """

    def __init__(self, secret: Optional[str]):
        """
        Initialize the verifier with a shared secret.

        Args:
            secret: The webhook secret configured in GitHub and the application.
        """
        self.secret = secret

    def generate_signature(self, payload: bytes) -> str:
        """
        Compute the HMAC SHA-256 signature for the given payload.

        Args:
            payload: The raw request body bytes.

        Returns:
            The computed signature prefixed with 'sha256='.
            
        Raises:
            MissingSecretError: If the webhook secret is not configured.
        """
        if not self.secret:
            raise MissingSecretError("Webhook secret is not configured.")

        # HMAC requires bytes for both key and message
        secret_bytes = self.secret.encode("utf-8")
        
        # Enforce SHA-256 as per modern GitHub standards (X-Hub-Signature-256)
        mac = hmac.new(secret_bytes, msg=payload, digestmod=hashlib.sha256)
        return f"sha256={mac.hexdigest()}"

    def verify_signature(self, payload: bytes, signature: Optional[str]) -> bool:
        """
        Verify the payload against the provided signature header.

        Args:
            payload: The raw request body bytes.
            signature: The value of the X-Hub-Signature-256 header.

        Returns:
            True if the signature is valid, False otherwise.
            
        Raises:
            MissingSecretError: If the webhook secret is not configured.
        """
        # Edge case: Missing signature header
        if not signature:
            return False

        # Edge case: Invalid signature format or unsupported hash algorithm.
        # We only support 'sha256=' as it's the current GitHub standard.
        if not signature.startswith("sha256="):
            return False

        expected_signature = self.generate_signature(payload)

        # Security requirement: Always use hmac.compare_digest for constant-time
        # comparison. This prevents timing attacks where an attacker could deduce
        # the signature by analyzing response times for string inequalities.
        # NEVER use `expected_signature == signature`.
        return hmac.compare_digest(expected_signature, signature)
