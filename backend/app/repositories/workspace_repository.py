from datetime import datetime, timezone
from typing import Optional, Sequence, Dict, Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import InvitationStatus, WorkspaceRole
from app.models.invitation import Invitation
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.base import BaseRepository
from app.schemas.workspace import WorkspaceCreateRequest, WorkspaceUpdate


class WorkspaceRepository(BaseRepository[Workspace]):
    """Repository handling database access only for the Workspace model."""

    def __init__(self, db: Session):
        super().__init__(Workspace, db)

    def create_workspace(self, schema: WorkspaceCreateRequest) -> Workspace:
        """Create a workspace record in the database."""
        workspace = Workspace(
            name=schema.name,
            slug=schema.slug,
            logo_url=str(schema.logo_url) if schema.logo_url else None,
            description=schema.description,
            is_active=schema.is_active,
        )
        self.db.add(workspace)
        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def get_workspace_by_id(self, workspace_id: UUID) -> Optional[Workspace]:
        """Fetch a workspace by its UUID."""
        return self.get(workspace_id)

    def get_workspace_by_slug(self, slug: str) -> Optional[Workspace]:
        """Fetch a workspace by its slug."""
        statement = select(Workspace).where(Workspace.slug == slug)
        return self.db.scalars(statement).first()

    def list_workspaces(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> Sequence[Workspace]:
        """List workspaces using the base repository filtering, sorting, and search."""
        return self.list(
            skip=skip,
            limit=limit,
            filters=filters,
            search=search,
            search_fields=["name", "slug", "description"],
            sort_by=sort_by,
        )

    def update_workspace(self, workspace_id: UUID, schema: WorkspaceUpdate) -> Optional[Workspace]:
        """Update a workspace record in the database."""
        workspace = self.get(workspace_id)
        if not workspace:
            return None

        update_data = schema.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "logo_url" and value is not None:
                setattr(workspace, key, str(value))
            else:
                setattr(workspace, key, value)

        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def update_workspace_fields(self, workspace_id: UUID, **fields: Any) -> Optional[Workspace]:
        """Apply explicit field updates to a workspace record."""
        workspace = self.get(workspace_id)
        if not workspace:
            return None

        for key, value in fields.items():
            if value is not None:
                setattr(workspace, key, value)

        self.db.commit()
        self.db.refresh(workspace)
        return workspace

    def delete_workspace(self, workspace_id: UUID) -> bool:
        """Delete a workspace record from the database."""
        return self.delete(workspace_id)

    def workspace_slug_exists(self, slug: str, exclude_workspace_id: Optional[UUID] = None) -> bool:
        """Check whether a workspace slug already exists."""
        statement = select(Workspace).where(Workspace.slug == slug)
        if exclude_workspace_id:
            statement = statement.where(Workspace.id != exclude_workspace_id)
        return self.db.scalars(statement).first() is not None

    def get_workspace_owner(self, workspace_id: UUID) -> Optional[WorkspaceMember]:
        """Fetch the current owner membership for a workspace."""
        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.role == WorkspaceRole.OWNER,
        )
        return self.db.scalars(statement).first()

    def update_member_role(self, workspace_id: UUID, user_id: UUID, role: WorkspaceRole) -> Optional[WorkspaceMember]:
        """Update the role of a workspace member."""
        member = self.get_member(workspace_id, user_id)
        if not member:
            return None

        member.role = role
        self.db.commit()
        self.db.refresh(member)
        return member

    def list_user_workspaces(self, user_id: UUID) -> Sequence[Workspace]:
        """List all workspaces that a user is a member of."""
        statement = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
        )
        return self.db.scalars(statement).all()

    def add_member(self, workspace_id: UUID, user_id: UUID, role) -> WorkspaceMember:
        """Add a member to a workspace if they are not already present."""
        existing = self.get_member(workspace_id, user_id)
        if existing is not None:
            return existing

        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def remove_member(self, workspace_id: UUID, user_id: UUID) -> bool:
        """Remove a member from a workspace."""
        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        member = self.db.scalars(statement).first()
        if member:
            self.db.delete(member)
            self.db.commit()
            return True
        return False

    def get_member(self, workspace_id: UUID, user_id: UUID) -> Optional[WorkspaceMember]:
        """Fetch a specific member record."""
        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        return self.db.scalars(statement).first()

    def list_members(self, workspace_id: UUID) -> Sequence[WorkspaceMember]:
        """List all members of a workspace."""
        from sqlalchemy.orm import joinedload
        statement = (
            select(WorkspaceMember)
            .options(joinedload(WorkspaceMember.user))
            .where(WorkspaceMember.workspace_id == workspace_id)
        )
        return self.db.scalars(statement).all()

    def owner_exists(self, workspace_id: UUID, exclude_user_id: Optional[UUID] = None) -> bool:
        """Check if at least one OWNER exists in the workspace."""
        from app.models.enums import WorkspaceRole

        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.role == WorkspaceRole.OWNER,
        )
        if exclude_user_id:
            statement = statement.where(WorkspaceMember.user_id != exclude_user_id)

        member = self.db.scalars(statement).first()
        return member is not None

    def get_invitation_by_token(self, token: str) -> Optional[Invitation]:
        """Fetch an invitation by token with workspace and inviter loaded."""
        from sqlalchemy.orm import joinedload
        statement = (
            select(Invitation)
            .options(joinedload(Invitation.workspace), joinedload(Invitation.inviter))
            .where(Invitation.token == token)
        )
        return self.db.scalars(statement).first()

    def get_invitation(self, invitation_id: UUID) -> Optional[Invitation]:
        """Fetch an invitation by id."""
        return self.db.get(Invitation, invitation_id)

    def get_pending_invitation(self, token: str) -> Optional[Invitation]:
        """Fetch a pending invitation by token."""
        statement = select(Invitation).where(
            Invitation.token == token,
            Invitation.status == InvitationStatus.PENDING,
        )
        return self.db.scalars(statement).first()

    def get_pending_invitation_by_workspace_and_email(self, workspace_id: UUID, email: str) -> Optional[Invitation]:
        """Fetch a pending invitation for a given workspace/email pair."""
        statement = select(Invitation).where(
            Invitation.workspace_id == workspace_id,
            Invitation.email == email,
            Invitation.status == InvitationStatus.PENDING,
        )
        return self.db.scalars(statement).first()

    def get_all_pending_invitations_by_email(self, email: str) -> Sequence[Invitation]:
        """Fetch all pending invitations for a given email."""
        statement = select(Invitation).where(
            Invitation.email == email,
            Invitation.status == InvitationStatus.PENDING,
        )
        return self.db.scalars(statement).all()

    def get_invitation_by_workspace_and_email(self, workspace_id: UUID, email: str) -> Optional[Invitation]:
        """Fetch an invitation for a given workspace/email pair."""
        statement = select(Invitation).where(
            Invitation.workspace_id == workspace_id,
            Invitation.email == email,
        )
        return self.db.scalars(statement).first()

    def create_invitation(self, workspace_id: UUID, email: str, role, token: str, expires_at: datetime, inviter_id: UUID) -> Invitation:
        """Create a new invitation record."""
        invitation = Invitation(
            workspace_id=workspace_id,
            email=email,
            role=role,
            token=token,
            status=InvitationStatus.PENDING,
            expires_at=expires_at,
            inviter_id=inviter_id,
        )
        self.db.add(invitation)
        self.db.commit()
        self.db.refresh(invitation)
        return invitation

    def mark_invitation_accepted(self, invitation_id: UUID) -> Optional[Invitation]:
        """Mark an invitation as accepted."""
        invitation = self.get_invitation(invitation_id)
        if invitation:
            invitation.status = InvitationStatus.ACCEPTED
            invitation.accepted_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(invitation)
        return invitation

    def mark_invitation_declined(self, invitation_id: UUID) -> Optional[Invitation]:
        """Mark an invitation as declined."""
        invitation = self.get_invitation(invitation_id)
        if invitation:
            invitation.status = InvitationStatus.DECLINED
            self.db.commit()
            self.db.refresh(invitation)
        return invitation

    def mark_invitation_cancelled(self, invitation_id: UUID) -> Optional[Invitation]:
        """Mark an invitation as cancelled."""
        invitation = self.get_invitation(invitation_id)
        if invitation:
            invitation.status = InvitationStatus.CANCELLED
            self.db.commit()
            self.db.refresh(invitation)
        return invitation

    def mark_invitation_expired(self, invitation_id: UUID) -> Optional[Invitation]:
        """Mark an invitation as expired."""
        invitation = self.get_invitation(invitation_id)
        if invitation:
            invitation.status = InvitationStatus.EXPIRED
            self.db.commit()
            self.db.refresh(invitation)
        return invitation

    def update_invitation_expiry(self, invitation_id: UUID, expires_at: datetime) -> Optional[Invitation]:
        """Refresh the expiry timestamp for an invitation."""
        invitation = self.get_invitation(invitation_id)
        if invitation:
            invitation.expires_at = expires_at
            self.db.commit()
            self.db.refresh(invitation)
        return invitation
