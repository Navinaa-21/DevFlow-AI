from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.repository import (
    RepositoryCreateRequest,
    RepositoryResponse,
    RepositoryUpdateRequest,
)
from app.services.repository_service import (
    RepositoryConflictError,
    RepositoryNotFoundError,
    RepositoryPermissionError,
    RepositoryService,
    RepositoryServiceError,
    WorkspaceAccessDeniedError,
)
from app.utils.webhook_signature import GitHubWebhookVerifier, MissingSecretError

router = APIRouter(tags=["Repositories"])


def _handle_service_error(error: RepositoryServiceError) -> None:
    if isinstance(error, RepositoryNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, WorkspaceAccessDeniedError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    if isinstance(error, RepositoryPermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    if isinstance(error, RepositoryConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post(
    "/workspaces/{workspace_id}/repositories",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a repository connection",
    description="Create a repository entry for a workspace.",
)
def create_repository(
    workspace_id: UUID,
    payload: RepositoryCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = RepositoryService(db)
    try:
        return service.connect_repository(workspace_id, current_user, payload)
    except RepositoryServiceError as error:
        _handle_service_error(error)


@router.get(
    "/workspaces/{workspace_id}/repositories",
    response_model=Sequence[RepositoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List repositories for a workspace",
    description="List repositories connected to the specified workspace.",
)
def list_repositories(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = RepositoryService(db)
    try:
        return service.list_repositories(workspace_id, current_user)
    except RepositoryServiceError as error:
        _handle_service_error(error)


@router.get(
    "/repositories/{repository_id}",
    response_model=RepositoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get repository details",
    description="Retrieve a single repository by ID.",
)
def get_repository(
    repository_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = RepositoryService(db)
    try:
        return service.get_repository(repository_id, current_user)
    except RepositoryServiceError as error:
        _handle_service_error(error)


@router.patch(
    "/repositories/{repository_id}",
    response_model=RepositoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update repository details",
    description="Update repository metadata such as name, default branch, or visibility.",
)
def update_repository(
    repository_id: UUID,
    payload: RepositoryUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = RepositoryService(db)
    try:
        return service.update_repository(repository_id, current_user, payload)
    except RepositoryServiceError as error:
        _handle_service_error(error)


@router.delete(
    "/repositories/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a repository",
    description="Remove a repository connection from the workspace.",
)
def delete_repository(
    repository_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = RepositoryService(db)
    try:
        service.delete_repository(repository_id, current_user)
        return None
    except RepositoryServiceError as error:
        _handle_service_error(error)


@router.post(
    "/repositories/{repository_id}/sync",
    status_code=status.HTTP_200_OK,
    summary="Manually sync repository metadata",
    description="Fetch the latest repository metadata from GitHub and update the local record.",
)
def sync_repository(
    repository_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = RepositoryService(db)
    try:
        return service.sync_repository(repository_id, current_user)
    except RepositoryServiceError as error:
        _handle_service_error(error)


@router.post(
    "/repositories/webhook",
    status_code=status.HTTP_200_OK,
    summary="Receive GitHub repository webhooks",
    description="Verify the payload signature and store the webhook event for the connected repository.",
)
async def repository_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    payload_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    delivery_id = request.headers.get("X-GitHub-Delivery")
    event_type = request.headers.get("X-GitHub-Event")

    if not signature or not delivery_id or not event_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing webhook headers")

    verifier = GitHubWebhookVerifier(secret=settings.GITHUB_WEBHOOK_SECRET)
    try:
        if not verifier.verify_signature(payload_bytes, signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid GitHub webhook signature")
    except MissingSecretError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    payload = {} if not payload_bytes else __import__("json").loads(payload_bytes.decode("utf-8"))
    service = RepositoryService(db)
    try:
        return service.ingest_webhook(payload, delivery_id, event_type)
    except RepositoryServiceError as error:
        _handle_service_error(error)


@router.get(
    "/repositories/{repository_id}/sync-status",
    status_code=status.HTTP_200_OK,
    summary="Get sync status",
    description="Return the last sync metadata for the repository.",
)
def get_sync_status(
    repository_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = RepositoryService(db)
    try:
        return service.get_sync_status(repository_id, current_user)
    except RepositoryServiceError as error:
        _handle_service_error(error)
