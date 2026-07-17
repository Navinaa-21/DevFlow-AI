import unittest
from unittest.mock import MagicMock
from uuid import uuid4
import json

from app.models.enums import WebhookProcessingStatus
from app.services.webhook_service import (
    WebhookService,
    InvalidSignatureError,
    PayloadParseError,
    RepositoryNotFoundError
)


class TestWebhookService(unittest.TestCase):
    def setUp(self):
        self.webhook_repo = MagicMock()
        self.commit_repo = MagicMock()
        self.repository_repo = MagicMock()
        self.verifier = MagicMock()
        
        self.service = WebhookService(
            webhook_repo=self.webhook_repo,
            commit_repo=self.commit_repo,
            repository_repo=self.repository_repo,
            verifier=self.verifier,
        )
        
        self.repository_id = uuid4()
        self.delivery_id = "test-delivery-id"
        self.event_type = "push"
        
        self.payload_dict = {
            "ref": "refs/heads/main",
            "commits": [
                {
                    "id": "1234567890abcdef",
                    "message": "Initial commit",
                    "timestamp": "2023-01-01T12:00:00Z",
                    "author": {"name": "Test User", "email": "test@example.com"}
                }
            ]
        }
        self.payload_bytes = json.dumps(self.payload_dict).encode("utf-8")
        self.signature_header = "sha256=mocked_signature"

    def test_invalid_signature(self):
        self.verifier.verify_signature.return_value = False
        with self.assertRaises(InvalidSignatureError):
            self.service.process_github_webhook(
                self.repository_id,
                self.payload_bytes,
                "invalid",
                self.delivery_id,
                self.event_type
            )

    def test_invalid_payload(self):
        self.verifier.verify_signature.return_value = True
        with self.assertRaises(PayloadParseError):
            self.service.process_github_webhook(
                self.repository_id,
                b"invalid json",
                self.signature_header,
                self.delivery_id,
                self.event_type
            )

    def test_duplicate_delivery(self):
        self.verifier.verify_signature.return_value = True
        self.webhook_repo.get_by_delivery_id.return_value = MagicMock()
        
        result = self.service.process_github_webhook(
            self.repository_id,
            self.payload_bytes,
            self.signature_header,
            self.delivery_id,
            self.event_type
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["message"], "Already processed")
        self.repository_repo.get_repository_by_id.assert_not_called()

    def test_repository_not_found(self):
        self.verifier.verify_signature.return_value = True
        self.webhook_repo.get_by_delivery_id.return_value = None
        self.repository_repo.get_repository_by_id.return_value = None
        
        with self.assertRaises(RepositoryNotFoundError):
            self.service.process_github_webhook(
                self.repository_id,
                self.payload_bytes,
                self.signature_header,
                self.delivery_id,
                self.event_type
            )

    def test_unsupported_event(self):
        self.verifier.verify_signature.return_value = True
        self.webhook_repo.get_by_delivery_id.return_value = None
        self.repository_repo.get_repository_by_id.return_value = MagicMock()
        
        mock_webhook_event = MagicMock()
        self.webhook_repo.create_webhook_event.return_value = mock_webhook_event
        
        result = self.service.process_github_webhook(
            self.repository_id,
            self.payload_bytes,
            self.signature_header,
            self.delivery_id,
            "issues"
        )
        self.assertEqual(result["status"], "success")
        self.assertIn("Ignored", result["message"])
        self.webhook_repo.mark_ignored.assert_called_once_with(mock_webhook_event)
        self.commit_repo.bulk_create_commits.assert_not_called()

    def test_successful_push_processing(self):
        self.verifier.verify_signature.return_value = True
        self.webhook_repo.get_by_delivery_id.return_value = None
        self.repository_repo.get_repository_by_id.return_value = MagicMock()
        
        mock_webhook_event = MagicMock(id=uuid4())
        self.webhook_repo.create_webhook_event.return_value = mock_webhook_event
        self.commit_repo.commit_exists.return_value = False
        
        result = self.service.process_github_webhook(
            self.repository_id,
            self.payload_bytes,
            self.signature_header,
            self.delivery_id,
            "push"
        )
        
        self.assertEqual(result["status"], "success")
        self.assertIn("Processed 1 commits", result["message"])
        self.webhook_repo.mark_processed.assert_called_once_with(mock_webhook_event)
        self.commit_repo.bulk_create_commits.assert_called_once()
        
        # Verify extracted commit attributes
        created_commits = self.commit_repo.bulk_create_commits.call_args[0][0]
        self.assertEqual(len(created_commits), 1)
        commit = created_commits[0]
        self.assertEqual(commit.github_commit_sha, "1234567890abcdef")
        self.assertEqual(commit.branch, "main")


if __name__ == "__main__":
    unittest.main()
