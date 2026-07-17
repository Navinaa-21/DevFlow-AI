from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.invitation import InvitationCreate
from app.schemas.workspace import (
    TransferOwnershipRequest,
    WorkspaceCreateRequest,
    WorkspaceListResponse,
    WorkspaceMemberResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])
invitation_router = APIRouter(tags=["Invitations"])


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workspace",
    description="Create a new workspace and make the current user the initial owner.",
)
def create_workspace(
    schema: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    return service.create_workspace(current_user, schema)


@router.get(
    "",
    response_model=WorkspaceListResponse,
    status_code=status.HTTP_200_OK,
    summary="List my workspaces",
    description="Retrieve the workspaces visible to the current authenticated user.",
)
def list_workspaces(
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=100, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search term matching name, slug, or description"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    sort_by: Optional[str] = Query(None, description="Sort field name (prefix with '-' for descending)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    return service.list_my_workspaces(current_user)


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get workspace by ID",
    description="Retrieve details of a single workspace by its unique UUID.",
)
def get_workspace_by_id(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    return service.get_workspace(workspace_id, current_user)


@router.get("/by-slug/{slug}", response_model=WorkspaceResponse)
def get_workspace_by_slug(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    return service.get_workspace_by_slug(slug, current_user)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a workspace",
    description="Apply partial updates to a workspace.",
)
def update_workspace(
    workspace_id: UUID,
    schema: WorkspaceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    return service.update_workspace(workspace_id, current_user, schema)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a workspace",
    description="Permanently delete a workspace from the database.",
)
def delete_workspace(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    service.delete_workspace(workspace_id, current_user)
    return None


@router.post(
    "/{workspace_id}/transfer-ownership",
    status_code=status.HTTP_200_OK,
    summary="Transfer workspace ownership",
    description="Transfer ownership of a workspace to an existing member.",
)
def transfer_ownership(
    workspace_id: UUID,
    payload: TransferOwnershipRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    service.transfer_ownership(workspace_id, current_user, payload.new_owner_id)
    return {"message": "Ownership transferred successfully"}


@router.post(
    "/{workspace_id}/invitations",
    status_code=status.HTTP_201_CREATED,
    summary="Invite a member",
    description="Invite a new member to join the workspace.",
)
def create_invitation(
    workspace_id: UUID,
    payload: InvitationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    invitation = service.invite_member(current_user, workspace_id, str(payload.email), payload.role)
    return {
        "id": str(invitation.id),
        "email": invitation.email,
        "role": invitation.role.value.lower(),
        "status": invitation.status.value.lower(),
        "expires_at": invitation.expires_at.isoformat(),
    }


@router.get(
    "/{workspace_id}/members",
    response_model=list[WorkspaceMemberResponse],
    summary="List workspace members",
    description="Retrieve all registered users who belong to this workspace.",
)
def list_workspace_members(
    workspace_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    members = service.list_workspace_members(workspace_id, current_user)
    return [
        WorkspaceMemberResponse(
            id=member.user.id,
            full_name=member.user.full_name,
            email=member.user.email,
            role=member.role.value.lower(),
        )
        for member in members
    ]


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a member",
    description="Remove an existing workspace member.",
)
def remove_workspace_member(
    workspace_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    service.remove_member(current_user, workspace_id, user_id)
    return {"deleted": True}


@router.get("/invitations/{token}", status_code=status.HTTP_200_OK)
def get_invitation(token: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = WorkspaceService(db)
    invitation = service.repository.get_invitation_by_token(token)
    if not invitation:
        raise ValueError("Invitation not found")
    return {
        "id": str(invitation.id),
        "email": invitation.email,
        "status": invitation.status.value.lower(),
        "workspace_name": invitation.workspace.name if invitation.workspace else "Unknown Workspace",
        "inviter_name": invitation.inviter.full_name if getattr(invitation, "inviter", None) else "Someone",
        "role": invitation.role.value.lower()
    }


@invitation_router.get("/invitations/{token}", status_code=status.HTTP_200_OK)
def invitation_get(token: str, db: Session = Depends(get_db)):
    service = WorkspaceService(db)
    invitation = service.repository.get_invitation_by_token(token)
    if not invitation:
        raise ValueError("Invitation not found")
    return {
        "id": str(invitation.id),
        "email": invitation.email,
        "status": invitation.status.value.lower(),
        "workspace_name": invitation.workspace.name if invitation.workspace else "Unknown Workspace",
        "inviter_name": invitation.inviter.full_name if getattr(invitation, "inviter", None) else "Someone",
        "role": invitation.role.value.lower()
    }


@invitation_router.post("/invitations/{token}/accept", status_code=status.HTTP_200_OK)
def invitation_accept(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    invitation = service.accept_invitation(token, current_user)
    return {"id": str(invitation.id), "status": invitation.status.value.lower()}


@invitation_router.post("/invitations/{token}/decline", status_code=status.HTTP_200_OK)
def invitation_decline(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    invitation = service.decline_invitation(token, current_user)
    return {"id": str(invitation.id), "status": invitation.status.value.lower()}


@router.post("/invitations/{token}/accept", status_code=status.HTTP_200_OK)
def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    invitation = service.accept_invitation(token, current_user)
    return {"id": str(invitation.id), "status": invitation.status.value.lower()}


@router.post("/invitations/{token}/decline", status_code=status.HTTP_200_OK)
def decline_invitation(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    invitation = service.decline_invitation(token, current_user)
    return {"id": str(invitation.id), "status": invitation.status.value.lower()}


@router.post("/{workspace_id}/invitations/{invitation_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_invitation(
    workspace_id: UUID,
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    invitation = service.cancel_invitation(workspace_id, invitation_id, current_user)
    return {"id": str(invitation.id), "status": invitation.status.value.lower()}


@router.post("/{workspace_id}/invitations/{invitation_id}/resend", status_code=status.HTTP_200_OK)
def resend_invitation(
    workspace_id: UUID,
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkspaceService(db)
    invitation = service.resend_invitation(workspace_id, invitation_id, current_user)
    return {"id": str(invitation.id), "status": invitation.status.value.lower()}
