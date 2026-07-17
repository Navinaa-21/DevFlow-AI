import re
import logging
from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import RepositoryProvider, WorkspaceRole, WebhookProcessingStatus
from app.models.repository import Repository
from app.models.user import User
from app.models.webhook_event import WebhookEvent
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.webhook_repository import WebhookRepository
from app.utils.github_client import GitHubClient, GitHubClientError


logger = logging.getLogger(__name__)


class RepositoryServiceError(Exception):
    """Base exception for repository domain errors."""


class RepositoryNotFoundError(RepositoryServiceError):
    """Raised when a repository or workspace cannot be found."""


class WorkspaceAccessDeniedError(RepositoryServiceError):
    """Raised when the current user is not a member of the workspace."""


class RepositoryPermissionError(RepositoryServiceError):
    """Raised when the current user lacks repository management permissions."""


class RepositoryConflictError(RepositoryServiceError):
    """Raised when a duplicate repository is detected."""


class RepositoryAlreadyExistsError(RepositoryServiceError):
    """Compatibility exception for repository duplication handling."""


class GitHubTokenMissingError(RepositoryServiceError):
    """Compatibility exception for GitHub-linked account errors."""


class GitHubConnectionError(RepositoryServiceError):
    """Compatibility exception for GitHub API connection problems."""


def parse_github_url(url: str) -> tuple[str, str]:
    """
    Extract owner and repository name from a GitHub clone_url or repo_url.
    Matches formats like:
      - https://github.com/owner/repo.git
      - git@github.com:owner/repo.git
      - https://github.com/owner/repo
    """
    match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?", url)
    if match:
        return match.group(1), match.group(2)
    raise ValueError("Invalid GitHub URL format")


class RepositoryService:
    """Service layer for workspace repository CRUD and access-control rules."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = RepositoryRepository(db)
        self.webhook_repository = WebhookRepository(db)

    def _get_workspace(self, workspace_id: UUID) -> Workspace:
        workspace = self.db.get(Workspace, workspace_id)
        if not workspace:
            raise RepositoryNotFoundError("Workspace not found.")
        return workspace

    def _get_membership(self, workspace_id: UUID, user_id: UUID) -> WorkspaceMember:
        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        membership = self.db.scalars(statement).first()
        if not membership:
            raise WorkspaceAccessDeniedError("You are not a member of this workspace.")
        return membership

    def connect_repository(self, workspace_id: UUID, current_user: User, payload) -> Repository:
        self._get_workspace(workspace_id)
        membership = self._get_membership(workspace_id, current_user.id)
        if membership.role not in {WorkspaceRole.OWNER, WorkspaceRole.MANAGER}:
            raise RepositoryPermissionError("Only owners and managers can create repositories.")

        existing = self.repository.get_repository_by_provider_id(payload.provider, payload.provider_repository_id)
        if existing and existing.workspace_id == workspace_id:
            raise RepositoryConflictError("A repository with this provider ID is already connected to this workspace.")

        # Determine full_name and repo_url using URL parsing helper
        full_name = None
        repo_url = None
        if payload.provider == RepositoryProvider.GITHUB:
            try:
                owner, repo_name = parse_github_url(payload.clone_url)
                full_name = f"{owner}/{repo_name}"
                repo_url = f"https://github.com/{owner}/{repo_name}"
            except ValueError:
                pass

        # Create local repository object
        repo = self.repository.create_repository(
            workspace_id=workspace_id,
            provider=payload.provider,
            provider_repo_id=payload.provider_repository_id,
            name=payload.name,
            clone_url=payload.clone_url,
            default_branch=payload.default_branch or "main",
            visibility=payload.visibility,
            full_name=full_name,
            repo_url=repo_url,
            is_active=True,
        )

        # Trigger webhook registration if GITHUB
        if repo.provider == RepositoryProvider.GITHUB:
            try:
                access_token = None
                statement = select(User).where(User.id == current_user.id)
                user = self.db.scalars(statement).first()
                if user and getattr(user, "github_access_token", None):
                    access_token = user.github_access_token

                if not access_token:
                    access_token = "mock-github-access-token"

                owner, repo_name = parse_github_url(repo.clone_url)
                client = GitHubClient(access_token)
                
                webhook_url = f"{settings.WEBHOOK_BASE_URL}/repositories/webhook"
                webhook_secret = settings.GITHUB_WEBHOOK_SECRET or "mock-secret"

                __import__("asyncio").run(
                    client.create_webhook(owner, repo_name, webhook_url, webhook_secret)
                )
                
                # Mark webhook enabled upon success
                repo.webhook_enabled = True
                self.db.commit()
                self.db.refresh(repo)
            except Exception as error:
                logger.error(f"Failed to register GitHub webhook: {error}")
                raise GitHubConnectionError(f"Failed to register webhook on GitHub: {error}") from error

        return repo

    def list_repositories(self, workspace_id: UUID, current_user: User) -> Sequence[Repository]:
        self._get_workspace(workspace_id)
        self._get_membership(workspace_id, current_user.id)
        return self.repository.list_workspace_repositories(workspace_id)

    def get_repository(self, repository_id: UUID, current_user: User) -> Repository:
        repository = self.repository.get_repository_by_id(repository_id)
        if not repository:
            raise RepositoryNotFoundError("Repository not found.")

        self._get_membership(repository.workspace_id, current_user.id)
        return repository

    def update_repository(self, repository_id: UUID, current_user: User, payload) -> Repository:
        repository = self.repository.get_repository_by_id(repository_id)
        if not repository:
            raise RepositoryNotFoundError("Repository not found.")

        membership = self._get_membership(repository.workspace_id, current_user.id)
        if membership.role not in {WorkspaceRole.OWNER, WorkspaceRole.MANAGER}:
            raise RepositoryPermissionError("Only owners and managers can update repositories.")

        fields = payload.model_dump(exclude_unset=True)
        if not fields:
            return repository

        updated = self.repository.update_repository(repository_id, **fields)
        if not updated:
            raise RepositoryNotFoundError("Repository not found.")
        return updated

    def delete_repository(self, repository_id: UUID, current_user: User) -> None:
        repository = self.repository.get_repository_by_id(repository_id)
        if not repository:
            raise RepositoryNotFoundError("Repository not found.")

        membership = self._get_membership(repository.workspace_id, current_user.id)
        if membership.role not in {WorkspaceRole.OWNER, WorkspaceRole.MANAGER}:
            raise RepositoryPermissionError("Only owners and managers can delete repositories.")

        # Clean up webhook on GitHub if enabled
        if repository.provider == RepositoryProvider.GITHUB and repository.webhook_enabled:
            try:
                access_token = None
                statement = select(User).where(User.id == current_user.id)
                user = self.db.scalars(statement).first()
                if user and getattr(user, "github_access_token", None):
                    access_token = user.github_access_token

                if not access_token:
                    access_token = "mock-github-access-token"

                owner, repo_name = parse_github_url(repository.clone_url)
                client = GitHubClient(access_token)
                webhook_url = f"{settings.WEBHOOK_BASE_URL}/repositories/webhook"

                __import__("asyncio").run(
                    client.delete_webhook(owner, repo_name, webhook_url)
                )
            except Exception as error:
                logger.warning(f"Failed to clean up webhook on GitHub during repository connection removal: {error}")
                # Proceed with local deletion anyway so client connection isn't permanently locked
                pass

        deleted = self.repository.delete_repository(repository_id)
        if not deleted:
            raise RepositoryNotFoundError("Repository not found.")

    def sync_repository(self, repository_id: UUID, current_user: User) -> dict:
        repository = self.repository.get_repository_by_id(repository_id)
        if not repository:
            raise RepositoryNotFoundError("Repository not found.")

        self._get_membership(repository.workspace_id, current_user.id)

        if repository.provider != RepositoryProvider.GITHUB:
            raise RepositoryServiceError("Only GitHub repositories can be synced.")

        access_token = None
        statement = select(User).where(User.id == current_user.id)
        user = self.db.scalars(statement).first()
        if user and getattr(user, "github_access_token", None):
            access_token = user.github_access_token

        if not access_token:
            access_token = "mock-github-access-token"

        client = GitHubClient(access_token)
        try:
            owner, repo_name = parse_github_url(repository.clone_url)
        except ValueError as error:
            raise RepositoryServiceError(str(error)) from error

        try:
            matching = __import__("asyncio").run(client.get_repository_metadata(owner, repo_name))
        except GitHubClientError as error:
            if getattr(error, "status_code", None) == 404:
                raise RepositoryNotFoundError("Repository metadata could not be found on GitHub.") from error
            raise RepositoryServiceError(str(error)) from error

        repository.name = matching.get("name") or repository.name
        repository.default_branch = matching.get("default_branch") or repository.default_branch
        repository.visibility = "private" if matching.get("private") else "public"
        if "archived" in matching:
            repository.is_active = not matching.get("archived")
        repository.last_synced_at = datetime.now(timezone.utc)
        repository.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(repository)

        return {
            "repository_id": str(repository.id),
            "sync_status": "success",
            "default_branch": repository.default_branch,
            "visibility": repository.visibility,
            "last_synced_at": repository.last_synced_at.isoformat() if repository.last_synced_at else None,
        }

    def get_sync_status(self, repository_id: UUID, current_user: User) -> dict:
        repository = self.repository.get_repository_by_id(repository_id)
        if not repository:
            raise RepositoryNotFoundError("Repository not found.")

        self._get_membership(repository.workspace_id, current_user.id)
        return {
            "repository_id": str(repository.id),
            "sync_status": "success" if repository.last_synced_at else "pending",
            "last_synced_at": repository.last_synced_at.isoformat() if repository.last_synced_at else None,
            "default_branch": repository.default_branch,
            "visibility": repository.visibility,
        }

    def ingest_webhook(self, payload: dict, delivery_id: str, event_type: str) -> dict:
        # Handle installation and installation_repositories events dynamically
        if event_type in ("installation", "installation_repositories"):
            action = payload.get("action")
            repos_added = []
            repos_removed = []

            if action in ("created", "unsuspend"):
                repos_added = payload.get("repositories", [])
            elif action in ("deleted", "suspend"):
                repos_removed = payload.get("repositories", [])
            elif action == "added":
                repos_added = payload.get("repositories_added", [])
                repos_removed = payload.get("repositories_removed", [])
            elif action == "removed":
                repos_removed = payload.get("repositories_removed", [])

            processed_count = 0
            for repo_info in repos_added:
                p_id = str(repo_info.get("id") or "")
                repo_obj = self.repository.get_repository_by_provider_id(RepositoryProvider.GITHUB, p_id)
                if repo_obj:
                    repo_obj.is_active = True
                    repo_obj.updated_at = datetime.now(timezone.utc)
                    self.db.commit()

                    sub_delivery_id = f"{delivery_id}-{p_id}"
                    if not self.webhook_repository.get_by_delivery_id(sub_delivery_id):
                        event = self.webhook_repository.create_webhook_event(
                            repository_id=repo_obj.id,
                            event_type=event_type,
                            delivery_id=sub_delivery_id,
                            payload=payload,
                        )
                        self.webhook_repository.update_processing_status(
                            event,
                            WebhookProcessingStatus.PROCESSED,
                            processed_at=datetime.now(timezone.utc)
                        )
                    processed_count += 1

            for repo_info in repos_removed:
                p_id = str(repo_info.get("id") or "")
                repo_obj = self.repository.get_repository_by_provider_id(RepositoryProvider.GITHUB, p_id)
                if repo_obj:
                    repo_obj.is_active = False
                    repo_obj.updated_at = datetime.now(timezone.utc)
                    self.db.commit()

                    sub_delivery_id = f"{delivery_id}-{p_id}"
                    if not self.webhook_repository.get_by_delivery_id(sub_delivery_id):
                        event = self.webhook_repository.create_webhook_event(
                            repository_id=repo_obj.id,
                            event_type=event_type,
                            delivery_id=sub_delivery_id,
                            payload=payload,
                        )
                        self.webhook_repository.update_processing_status(
                            event,
                            WebhookProcessingStatus.PROCESSED,
                            processed_at=datetime.now(timezone.utc)
                        )
                    processed_count += 1

            return {"status": "success", "message": f"Processed installation event for {processed_count} repositories"}

        # Process other standard repository-linked events
        repo_payload = payload.get("repository", {})
        provider_repo_id = str(repo_payload.get("id") or "")
        if not provider_repo_id:
            raise RepositoryServiceError("Repository ID missing from webhook payload.")

        repository = self.repository.get_repository_by_provider_id(RepositoryProvider.GITHUB, provider_repo_id)
        if not repository:
            raise RepositoryNotFoundError("Repository not found.")

        # Check for duplicate event processing
        existing_event = self.webhook_repository.get_by_delivery_id(delivery_id)
        if existing_event:
            return {"status": "success", "message": "Already processed"}

        event = self.webhook_repository.create_webhook_event(
            repository_id=repository.id,
            event_type=event_type,
            delivery_id=delivery_id,
            payload=payload,
        )

        if event_type == "repository":
            action = payload.get("action")
            if action == "deleted":
                repository.is_active = False
            elif action == "archived":
                repository.is_active = False
            elif action == "unarchived":
                repository.is_active = True

            repository.name = repo_payload.get("name") or repository.name
            repository.default_branch = repo_payload.get("default_branch") or repository.default_branch
            if "private" in repo_payload:
                repository.visibility = "private" if repo_payload["private"] else "public"
            if "archived" in repo_payload:
                repository.is_active = not repo_payload["archived"]

            repository.last_synced_at = datetime.now(timezone.utc)
            repository.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(repository)
            self.webhook_repository.update_processing_status(
                event,
                WebhookProcessingStatus.PROCESSED,
                processed_at=datetime.now(timezone.utc)
            )
            return {"status": "success", "message": "Processed repository event"}

        elif event_type == "push":
            from app.repositories.commit_repository import CommitRepository
            from app.services.webhook_service import WebhookService

            commit_repo = CommitRepository(self.db)
            webhook_service = WebhookService(
                webhook_repo=self.webhook_repository,
                commit_repo=commit_repo,
                repository_repo=self.repository,
                verifier=None
            )

            try:
                commits = webhook_service.extract_commits(
                    repository_id=repository.id,
                    webhook_event_id=event.id,
                    payload_dict=payload,
                )
                if commits:
                    webhook_service.persist_commits(commits)

                self.webhook_repository.update_processing_status(
                    event,
                    WebhookProcessingStatus.PROCESSED,
                    processed_at=datetime.now(timezone.utc)
                )
                return {"status": "success", "message": f"Processed {len(commits)} commits"}
            except Exception as e:
                self.webhook_repository.update_processing_status(
                    event,
                    WebhookProcessingStatus.FAILED,
                    error_message=str(e)
                )
                raise RepositoryServiceError(f"Push processing failed: {e}") from e

        else:
            self.webhook_repository.update_processing_status(
                event,
                WebhookProcessingStatus.IGNORED,
                processed_at=datetime.now(timezone.utc)
            )
            return {"status": "success", "message": f"Ignored event type: {event_type}"}
