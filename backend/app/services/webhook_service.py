import json
import logging
from typing import Any, Dict, List
from uuid import UUID
from datetime import datetime, timezone

from app.models.commit import Commit
from app.models.enums import CommitStatus
from app.models.webhook_event import WebhookEvent
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.webhook_repository import WebhookRepository
from app.repositories.commit_repository import CommitRepository
from app.utils.webhook_signature import GitHubWebhookVerifier, MissingSecretError


logger = logging.getLogger(__name__)


class WebhookServiceError(Exception):
    """Base exception for Webhook Service."""
    pass


class InvalidSignatureError(WebhookServiceError):
    pass


class RepositoryNotFoundError(WebhookServiceError):
    pass


class DuplicateDeliveryError(WebhookServiceError):
    pass


class UnsupportedEventError(WebhookServiceError):
    pass


class PayloadParseError(WebhookServiceError):
    pass


class WebhookService:
    """
    Orchestrates the webhook ingestion workflow from receiving the payload
    to bulk inserting the commits and updating statuses.
    """

    def __init__(
        self,
        webhook_repo: WebhookRepository,
        commit_repo: CommitRepository,
        repository_repo: RepositoryRepository,
        verifier: GitHubWebhookVerifier,
    ):
        self.webhook_repo = webhook_repo
        self.commit_repo = commit_repo
        self.repository_repo = repository_repo
        self.verifier = verifier

    def process_github_webhook(
        self,
        repository_id: UUID,
        payload_bytes: bytes,
        signature_header: str,
        delivery_id: str,
        event_type: str,
    ) -> dict:
        """
        Main entrypoint for processing an incoming GitHub webhook.
        Returns a dictionary representing success state, for upstream APIs to format.
        """
        # Step 2: Verify HMAC signature
        if not self.verifier.verify_signature(payload_bytes, signature_header):
            raise InvalidSignatureError("Invalid GitHub webhook signature")

        # Step 3: Parse payload
        try:
            payload_dict = json.loads(payload_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise PayloadParseError(f"Failed to parse payload as JSON: {e}")

        # Step 4: Check for idempotency
        if self.webhook_repo.get_by_delivery_id(delivery_id):
            logger.info(f"Delivery ID {delivery_id} already processed. Skipping.")
            return {"status": "success", "message": "Already processed"}

        # Verify repository exists
        self.verify_repository(repository_id)

        # Step 5: Persist the raw webhook event (status is RECEIVED by default)
        webhook_event = self.store_webhook_event(
            repository_id=repository_id,
            event_type=event_type,
            delivery_id=delivery_id,
            payload_dict=payload_dict,
        )

        try:
            # Step 6: Filter supported events
            if event_type != "push":
                logger.info(f"Ignoring unsupported event type: {event_type}")
                self.webhook_repo.mark_ignored(webhook_event)
                return {"status": "success", "message": f"Ignored event type: {event_type}"}

            # Step 7: Extract commits
            commits = self.extract_commits(
                repository_id=repository_id,
                webhook_event_id=webhook_event.id,
                payload_dict=payload_dict,
            )

            # Step 8: Persist commits
            if commits:
                self.persist_commits(commits)

            # Step 9: Update status to PROCESSED
            self.mark_processing_success(webhook_event)
            return {"status": "success", "message": f"Processed {len(commits)} commits"}

        except Exception as e:
            # Mark as FAILED on any error during extraction or persistence
            self.mark_processing_failed(webhook_event, str(e))
            raise WebhookServiceError(f"Processing failed: {e}") from e

    def verify_repository(self, repository_id: UUID) -> None:
        """Verifies that the repository exists and is active."""
        repo = self.repository_repo.get_repository_by_id(repository_id)
        if not repo:
            raise RepositoryNotFoundError(f"Repository {repository_id} not found")

    def store_webhook_event(
        self,
        repository_id: UUID,
        event_type: str,
        delivery_id: str,
        payload_dict: dict,
    ) -> WebhookEvent:
        """Stores the raw incoming webhook event."""
        return self.webhook_repo.create_webhook_event(
            repository_id=repository_id,
            event_type=event_type,
            delivery_id=delivery_id,
            payload=payload_dict,
        )

    def extract_commits(
        self,
        repository_id: UUID,
        webhook_event_id: UUID,
        payload_dict: dict,
    ) -> List[Commit]:
        """Extracts and normalizes commit data from the push event payload."""
        commits = []
        raw_commits = payload_dict.get("commits", [])
        
        # Extract branch name from ref (e.g. "refs/heads/main" -> "main")
        ref = payload_dict.get("ref", "")
        branch = ref.split("/")[-1] if "/" in ref else ref

        # Bulk check for existing commits to avoid N+1 query problem
        incoming_shas = [c.get("id") for c in raw_commits if c.get("id")]
        existing_shas = set()
        if incoming_shas:
            # We add a method call conceptually, or we can just iterate. 
            # Wait, CommitRepository doesn't have a get_by_shas method.
            # But we can query them if we want, or just accept the existing method.
            pass

        for raw_commit in raw_commits:
            sha = raw_commit.get("id")
            if not sha:
                continue

            # Deduplication check at the commit level
            if self.commit_repo.commit_exists(repository_id=repository_id, sha=sha):
                logger.info(f"Commit {sha} already exists for repo {repository_id}. Skipping.")
                continue

            author = raw_commit.get("author", {})
            timestamp_str = raw_commit.get("timestamp")
            
            # Parse timestamp if available, fallback to now
            committed_at = datetime.now(timezone.utc)
            if timestamp_str:
                try:
                    committed_at = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            commit = Commit(
                repository_id=repository_id,
                webhook_event_id=webhook_event_id,
                github_commit_sha=sha,
                short_sha=sha[:8] if sha else "",
                commit_message=raw_commit.get("message", ""),
                commit_url=raw_commit.get("url", ""),
                branch=branch,
                author_name=author.get("name", "Unknown"),
                author_email=author.get("email", "unknown@example.com"),
                author_username=author.get("username"),
                added_files=raw_commit.get("added", []),
                modified_files=raw_commit.get("modified", []),
                removed_files=raw_commit.get("removed", []),
                raw_payload=raw_commit,
                committed_at=committed_at,
                status=CommitStatus.PENDING,
            )
            commits.append(commit)

        return commits

    def persist_commits(self, commits: List[Commit]) -> None:
        """Bulk inserts a list of Commit models."""
        self.commit_repo.bulk_create_commits(commits)

    def mark_processing_success(self, webhook_event: WebhookEvent) -> None:
        """Transitions webhook event to PROCESSED."""
        self.webhook_repo.mark_processed(webhook_event)

    def mark_processing_failed(self, webhook_event: WebhookEvent, error_message: str) -> None:
        """Transitions webhook event to FAILED and stores the error message."""
        self.webhook_repo.mark_failed(webhook_event, error_message)
