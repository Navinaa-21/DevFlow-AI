import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import InvitationStatus, WorkspaceRole

if TYPE_CHECKING:
    from app.models.workspace import Workspace


class Invitation(BaseModel):
    __tablename__ = "invitations"

    __table_args__ = (
        Index(
            "uq_workspace_invite_email",
            "workspace_id",
            "email",
            unique=True,
            postgresql_where=text("status = 'PENDING'"),
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    inviter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(WorkspaceRole),
        nullable=False,
    )

    token: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    status: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus),
        nullable=False,
        default=InvitationStatus.PENDING,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    workspace: Mapped["Workspace"] = relationship(
        back_populates="invitations",
    )

    inviter: Mapped["User"] = relationship(
        "User",
        foreign_keys=[inviter_id]
    )