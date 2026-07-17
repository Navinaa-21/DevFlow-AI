from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.workspace_member import WorkspaceMember
    from app.models.repository import Repository
    from app.models.invitation import Invitation


class Workspace(BaseModel):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    logo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Members of the workspace
    members: Mapped[list["WorkspaceMember"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    # Connected repositories
    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )

    # Pending invitations
    invitations: Mapped[list["Invitation"]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )