import hashlib
import hmac


class GitHubWebhookVerifier:
    """
    Utility class for validating the authenticity of incoming GitHub webhook request payloads
    by verifying the HMAC SHA256 signature header.
    """
    def __init__(self, secret: str) -> None:
        self.secret = secret

    def verify_signature(self, payload: bytes, signature_header: str) -> bool:
        """
        Verifies the incoming webhook payload against the signature header.
        Raises ValueError if verification fails or the signature header is invalid.
        """
        if not signature_header:
            raise ValueError("Signature header is missing.")

        if not signature_header.startswith("sha256="):
            raise ValueError("Invalid signature header format. Expected 'sha256=<signature>'.")

        # Extract the signature hash (removing the 'sha256=' prefix)
        expected_signature = signature_header.split("sha256=")[-1].strip()

        # Compute HMAC SHA256 hash using the secret key and the raw payload body
        computed_signature = hmac.new(
            key=self.secret.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()

        # Compare the computed hash with the expected signature securely using constant-time comparison
        if not hmac.compare_digest(computed_signature, expected_signature):
            raise ValueError("HMAC signature verification failed. The payload has been modified or the secret is invalid.")

        return True
