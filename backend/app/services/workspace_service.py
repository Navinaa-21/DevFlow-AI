from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.enums import InvitationStatus, WorkspaceRole
from app.models.invitation import Invitation
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreateRequest, WorkspaceUpdate


class WorkspaceDomainError(Exception):
    """Base exception class for all Workspace domain errors."""
    pass


class WorkspaceNotFoundError(WorkspaceDomainError):
    """Raised when a requested workspace does not exist."""
    pass


class WorkspaceSlugConflictError(WorkspaceDomainError):
    """Raised when a workspace slug already exists in the system."""
    pass


class WorkspacePermissionError(WorkspaceDomainError):
    """Raised when the acting user lacks the required workspace permissions."""
    pass


class WorkspaceMembershipConflictError(WorkspaceDomainError):
    """Raised when a user is already a member of the workspace."""
    pass


class InvitationStateError(WorkspaceDomainError):
    """Raised when an invitation cannot transition to the requested state."""
    pass


class WorkspaceService:
    """Service class encapsulating business rules for Workspace management."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = WorkspaceRepository(db)

    def create_workspace(self, current_user: User, schema: WorkspaceCreateRequest) -> Workspace:
        """Create a workspace and set the creator as the initial OWNER."""
        if self.repository.get_workspace_by_slug(schema.slug):
            raise WorkspaceSlugConflictError("A workspace with this slug already exists.")

        workspace = self.repository.create_workspace(schema)
        self.repository.add_member(workspace.id, current_user.id, WorkspaceRole.OWNER)
        return workspace

    def list_my_workspaces(self, current_user: User) -> dict:
        """Return the workspaces visible to the current user."""
        items = self.repository.list_user_workspaces(current_user.id)
        return {
            "items": items,
            "total": len(items),
            "limit": len(items),
            "offset": 0,
        }

    def get_workspace(self, workspace_id: UUID, current_user: User) -> Workspace:
        """Fetch a workspace only if the current user is a member."""
        workspace = self.repository.get_workspace_by_id(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found.")
        if not self.repository.get_member(workspace_id, current_user.id):
            raise WorkspacePermissionError("You are not a member of this workspace.")
        return workspace

    def get_workspace_by_slug(self, slug: str, current_user: User) -> Workspace:
        """Fetch a workspace by slug only if the current user is a member."""
        workspace = self.repository.get_workspace_by_slug(slug)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found.")
        if not self.repository.get_member(workspace.id, current_user.id):
            raise WorkspacePermissionError("You are not a member of this workspace.")
        return workspace

    def list_workspace_members(self, workspace_id: UUID, current_user: User) -> list[WorkspaceMember]:
        """List members for a workspace the current user can access."""
        self.get_workspace(workspace_id, current_user)
        return list(self.repository.list_members(workspace_id))

    def invite_member(self, current_user: User, workspace_id: UUID, email: str, role: WorkspaceRole) -> Invitation:
        """Create an invitation for a user if the current user has managing rights."""
        workspace = self.repository.get_workspace_by_id(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found.")

        membership = self.repository.get_member(workspace_id, current_user.id)
        if not membership or membership.role not in {WorkspaceRole.OWNER, WorkspaceRole.MANAGER}:
            raise WorkspacePermissionError("Only owners and managers can invite members.")

        # target_user = self.db.query(User).filter(User.email == email).first()
        # The user has explicitly stated that we can invite non-registered users.
        
        # We only check membership if the user happens to exist.
        target_user = self.db.query(User).filter(User.email == email).first()
        if target_user and self.repository.get_member(workspace_id, target_user.id):
            raise WorkspaceMembershipConflictError("User is already a member of this workspace.")

        existing_invitation = self.repository.get_pending_invitation_by_workspace_and_email(workspace_id, email)
        if existing_invitation:
            raise InvitationStateError("An invitation for this email is already pending.")

        raw_token = uuid4().hex
        invitation = self.repository.create_invitation(
            workspace_id=workspace_id,
            email=email,
            role=role,
            token=raw_token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            inviter_id=current_user.id
        )
        
        from app.services.email_service import EmailService
        EmailService().send_invitation_email(
            to_email=email,
            token=raw_token,
            workspace_name=workspace.name,
            inviter_name=current_user.full_name,
            role=role.value
        )
        
        return invitation

    def remove_member(self, current_user: User, workspace_id: UUID, user_id: UUID) -> bool:
        """Remove a workspace member while preserving at least one owner."""
        workspace = self.repository.get_workspace_by_id(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found.")

        membership = self.repository.get_member(workspace_id, current_user.id)
        if not membership or membership.role not in {WorkspaceRole.OWNER, WorkspaceRole.MANAGER}:
            raise WorkspacePermissionError("Only owners and managers can remove members.")

        target_member = self.repository.get_member(workspace_id, user_id)
        if target_member is not None:
            if target_member.role == WorkspaceRole.OWNER and not self.repository.owner_exists(workspace_id, exclude_user_id=user_id):
                raise WorkspacePermissionError("Cannot remove the last owner.")

            self.repository.remove_member(workspace_id, user_id)
            return True

        target_user = self.db.query(User).filter(User.id == user_id).first()
        if not target_user:
            raise WorkspaceNotFoundError("Member not found.")

        invitation = self.repository.get_pending_invitation_by_workspace_and_email(workspace_id, target_user.email)
        if invitation:
            self.repository.mark_invitation_cancelled(invitation.id)
            return True

        raise WorkspaceNotFoundError("Member not found.")

    def list_workspaces(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> dict:
        """List workspaces delegating pagination, sorting, and filtering to the repository."""
        items = self.repository.list_workspaces(
            skip=skip,
            limit=limit,
            filters=filters,
            search=search,
            sort_by=sort_by,
        )
        total = self.repository.count(
            filters=filters,
            search=search,
            search_fields=["name", "slug", "description"],
        )
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": skip,
        }

    def update_workspace(self, workspace_id: UUID, current_user: Optional[User] = None, payload: Optional[WorkspaceUpdate] = None) -> Workspace:
        """Update workspace details while enforcing member permissions and slug uniqueness."""
        if payload is None and isinstance(current_user, WorkspaceUpdate):
            payload = current_user
            current_user = None

        if payload is None:
            payload = WorkspaceUpdate()

        workspace = self.repository.get_workspace_by_id(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found.")

        if current_user is not None:
            membership = self.repository.get_member(workspace_id, current_user.id)
            if not membership or membership.role not in {WorkspaceRole.OWNER, WorkspaceRole.MANAGER}:
                raise WorkspacePermissionError("Only owners and managers can update workspace details.")

        if payload.slug is not None:
            if self.repository.workspace_slug_exists(payload.slug, exclude_workspace_id=workspace_id):
                raise WorkspaceSlugConflictError("A workspace with this slug already exists.")

        updated_ws = self.repository.update_workspace(workspace_id, payload)
        if not updated_ws:
            raise WorkspaceNotFoundError("Workspace not found.")
        return updated_ws

    def delete_workspace(self, workspace_id: UUID, current_user: Optional[User] = None) -> None:
        """Delete a workspace after verifying ownership and existence."""
        workspace = self.repository.get_workspace_by_id(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found.")

        if current_user is not None:
            membership = self.repository.get_member(workspace_id, current_user.id)
            if not membership or membership.role != WorkspaceRole.OWNER:
                raise WorkspacePermissionError("Only the workspace owner can delete this workspace.")

        self.repository.delete_workspace(workspace_id)

    def transfer_ownership(self, workspace_id: UUID, current_owner: User, new_owner_id: UUID) -> WorkspaceMember:
        """Transfer workspace ownership to a current workspace member."""
        workspace = self.repository.get_workspace_by_id(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found.")

        current_membership = self.repository.get_member(workspace_id, current_owner.id)
        if not current_membership or current_membership.role != WorkspaceRole.OWNER:
            raise WorkspacePermissionError("Only the current owner can transfer ownership.")

        new_membership = self.repository.get_member(workspace_id, new_owner_id)
        if not new_membership:
            raise WorkspaceMembershipConflictError("The new owner must already be a member of the workspace.")

        if new_owner_id == current_owner.id:
            raise WorkspaceMembershipConflictError("The new owner must be a different workspace member.")

        self.repository.update_member_role(workspace_id, new_owner_id, WorkspaceRole.OWNER)
        self.repository.update_member_role(workspace_id, current_owner.id, WorkspaceRole.MANAGER)
        return new_membership

    def accept_invitation(self, token: str, current_user: User) -> Invitation:
        """Accept an invitation if it is valid for the current user."""
        invitation = self.repository.get_invitation_by_token(token)
        if not invitation:
            raise WorkspaceNotFoundError("Invitation not found.")

        if invitation.status == InvitationStatus.ACCEPTED:
            raise InvitationStateError("Invitation has already been accepted.")
        if invitation.status in {InvitationStatus.CANCELLED, InvitationStatus.DECLINED, InvitationStatus.EXPIRED}:
            raise InvitationStateError("Invitation is no longer pending.")
        if invitation.expires_at < datetime.now(timezone.utc):
            self.repository.mark_invitation_expired(invitation.id)
            raise InvitationStateError("Invitation has expired.")
        if invitation.email.lower() != current_user.email.lower():
            raise WorkspacePermissionError("This invitation is for a different email address.")
        if self.repository.get_member(invitation.workspace_id, current_user.id):
            raise WorkspaceMembershipConflictError("User is already a member of this workspace.")

        self.repository.add_member(invitation.workspace_id, current_user.id, invitation.role)
        return self.repository.mark_invitation_accepted(invitation.id)

    def decline_invitation(self, token: str, current_user: User) -> Invitation:
        """Decline an invitation if it is valid for the current user."""
        invitation = self.repository.get_invitation_by_token(token)
        if not invitation:
            raise WorkspaceNotFoundError("Invitation not found.")
        if invitation.status == InvitationStatus.ACCEPTED:
            raise InvitationStateError("Invitation has already been accepted.")
        if invitation.status != InvitationStatus.PENDING:
            raise InvitationStateError("Invitation is not pending.")
        if invitation.expires_at < datetime.now(timezone.utc):
            self.repository.mark_invitation_expired(invitation.id)
            raise InvitationStateError("Invitation has expired.")
        if invitation.email.lower() != current_user.email.lower():
            raise WorkspacePermissionError("This invitation is for a different email address.")
        return self.repository.mark_invitation_declined(invitation.id)

    def cancel_invitation(self, workspace_id: UUID, invitation_id: UUID, current_user: User) -> Invitation:
        """Cancel an invitation if the acting user has managing rights."""
        workspace = self.repository.get_workspace_by_id(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found.")

        membership = self.repository.get_member(workspace_id, current_user.id)
        if not membership or membership.role not in {WorkspaceRole.OWNER, WorkspaceRole.MANAGER}:
            raise WorkspacePermissionError("Only owners and managers can cancel invitations.")

        invitation = self.repository.get_invitation(invitation_id)
        if not invitation:
            raise WorkspaceNotFoundError("Invitation not found.")
        if invitation.status != InvitationStatus.PENDING:
            raise InvitationStateError("Invitation is not pending.")
        return self.repository.mark_invitation_cancelled(invitation.id)

    def resend_invitation(self, workspace_id: UUID, invitation_id: UUID, current_user: User) -> Invitation:
        """Resend an invitation to refresh its expiry date."""
        workspace = self.repository.get_workspace_by_id(workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError("Workspace not found.")

        membership = self.repository.get_member(workspace_id, current_user.id)
        if not membership or membership.role not in {WorkspaceRole.OWNER, WorkspaceRole.MANAGER}:
            raise WorkspacePermissionError("Only owners and managers can resend invitations.")

        invitation = self.repository.get_invitation(invitation_id)
        if not invitation:
            raise WorkspaceNotFoundError("Invitation not found.")
        if invitation.status != InvitationStatus.PENDING:
            raise InvitationStateError("Invitation is not pending.")

        new_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        updated_invitation = self.repository.update_invitation_expiry(invitation.id, new_expires_at)
        
        from app.services.email_service import EmailService
        # Eager load missing data since we might not have it in the standard invitation fetch
        inviter = self.db.get(User, invitation.inviter_id)
        EmailService().send_invitation_email(
            to_email=invitation.email,
            token=invitation.token,
            workspace_name=workspace.name,
            inviter_name=inviter.full_name if inviter else "Someone",
            role=invitation.role.value
        )
        return updated_invitation
