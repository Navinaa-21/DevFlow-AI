from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.commit_repository import CommitRepository
from app.utils.webhook_signature import GitHubWebhookVerifier
from app.core.config import settings
from app.models.commit import Commit


class WebhookService:
    """
    Service class responsible for validating, parsing, and persisting GitHub webhook events.
    """
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo_repo = RepositoryRepository(db)
        self.commit_repo = CommitRepository(db)
        self.verifier = GitHubWebhookVerifier(settings.GITHUB_WEBHOOK_SECRET)

    def process_webhook_payload(
        self,
        payload_bytes: bytes,
        signature_header: str,
        payload_json: Dict[str, Any]
    ) -> List[Commit]:
        """
        Validates webhook authenticity, verifies repository registration,
        extracts commit data, and persists new commits to the database.
        """
        # 1. Verify GitHub signature
        self.verifier.verify_signature(payload_bytes, signature_header)

        # 2. Check if repository is monitored
        repository_data = payload_json.get("repository")
        if not repository_data:
            raise ValueError("Invalid payload: repository details are missing.")

        github_repo_id = repository_data.get("id")
        if not github_repo_id:
            raise ValueError("Invalid payload: repository ID is missing.")

        db_repo = self.repo_repo.get_by_github_repo_id(int(github_repo_id))
        if not db_repo:
            raise ValueError(f"Repository with GitHub ID {github_repo_id} is not registered in this system.")

        if not db_repo.webhook_enabled:
            raise ValueError(f"Webhooks are disabled for repository: {db_repo.name}.")

        # 3. Extract and save commits
        commits_payload = payload_json.get("commits", [])
        persisted_commits: List[Commit] = []

        for commit_data in commits_payload:
            sha = commit_data.get("id")
            message = commit_data.get("message")
            author_info = commit_data.get("author", {})
            author_name = author_info.get("name", "Unknown")
            author_email = author_info.get("email", "")
            author_string = f"{author_name} <{author_email}>" if author_email else author_name
            
            timestamp_str = commit_data.get("timestamp")

            if not sha or not message or not timestamp_str:
                # Skip invalid or incomplete commit structures
                continue

            # Parse ISO timestamp to datetime
            try:
                # Replace 'Z' with '+00:00' to conform to standard ISO formatting if present
                if timestamp_str.endswith("Z"):
                    timestamp_str = timestamp_str[:-1] + "+00:00"
                committed_at = datetime.fromisoformat(timestamp_str)
            except Exception:
                committed_at = datetime.utcnow()

            # Persist unless it already exists
            if not self.commit_repo.commit_exists(sha):
                new_commit = self.commit_repo.create_commit(
                    repository_id=db_repo.id,
                    sha=sha,
                    message=message,
                    author=author_string,
                    committed_at=committed_at
                )
                persisted_commits.append(new_commit)
            else:
                # Retrieve the existing commit
                existing_commit = self.commit_repo.get_by_sha(sha)
                if existing_commit:
                    persisted_commits.append(existing_commit)

        return persisted_commits
