import unittest
from app.utils.webhook_signature import GitHubWebhookVerifier, MissingSecretError


class TestGitHubWebhookVerifier(unittest.TestCase):
    def setUp(self):
        self.secret = "my_super_secret_key"
        self.verifier = GitHubWebhookVerifier(secret=self.secret)
        self.payload = b'{"action": "push", "repository": {"name": "test-repo"}}'
        self.valid_signature = self.verifier.generate_signature(self.payload)

    def test_valid_signature(self):
        """Test that a valid signature returns True."""
        self.assertTrue(self.verifier.verify_signature(self.payload, self.valid_signature))

    def test_invalid_signature(self):
        """Test that an invalid signature returns False."""
        invalid_signature = "sha256=abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        self.assertFalse(self.verifier.verify_signature(self.payload, invalid_signature))

    def test_missing_signature(self):
        """Test that a missing signature returns False."""
        self.assertFalse(self.verifier.verify_signature(self.payload, None))
        self.assertFalse(self.verifier.verify_signature(self.payload, ""))

    def test_modified_payload(self):
        """Test that modifying the payload invalidates the signature."""
        modified_payload = b'{"action": "pull_request", "repository": {"name": "test-repo"}}'
        self.assertFalse(self.verifier.verify_signature(modified_payload, self.valid_signature))

    def test_empty_payload(self):
        """Test that an empty payload works as long as the signature is correct for an empty payload."""
        empty_payload = b""
        empty_signature = self.verifier.generate_signature(empty_payload)
        self.assertTrue(self.verifier.verify_signature(empty_payload, empty_signature))

    def test_missing_secret(self):
        """Test that initializing with no secret raises MissingSecretError on validation."""
        verifier = GitHubWebhookVerifier(secret=None)
        with self.assertRaises(MissingSecretError):
            verifier.verify_signature(self.payload, self.valid_signature)

    def test_unsupported_hash_algorithm(self):
        """Test that providing an unsupported hash algorithm prefix (e.g., sha1) returns False."""
        unsupported_signature = "sha1=abcdef1234567890abcdef1234567890abcdef12"
        self.assertFalse(self.verifier.verify_signature(self.payload, unsupported_signature))

    def test_invalid_signature_format(self):
        """Test that a signature without the sha256= prefix returns False."""
        invalid_format_signature = self.valid_signature.replace("sha256=", "")
        self.assertFalse(self.verifier.verify_signature(self.payload, invalid_format_signature))


if __name__ == "__main__":
    unittest.main()
