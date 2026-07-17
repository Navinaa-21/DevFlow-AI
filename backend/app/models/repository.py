import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import RepositoryProvider

if TYPE_CHECKING:
    from app.models.workspace import Workspace
    from app.models.webhook_event import WebhookEvent
    from app.models.commit import Commit


class Repository(BaseModel):
    __tablename__ = "repositories"

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "provider",
            "provider_repo_id",
            name="uq_workspace_provider_repo",
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider: Mapped[RepositoryProvider] = mapped_column(
        Enum(RepositoryProvider),
        nullable=False,
    )

    provider_repo_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    repo_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    clone_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    default_branch: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="main",
    )

    visibility: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="private",
    )

    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    webhook_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    workspace: Mapped["Workspace"] = relationship(
        back_populates="repositories",
    )

    webhook_events: Mapped[list["WebhookEvent"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
    )

    commits: Mapped[list["Commit"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
    )