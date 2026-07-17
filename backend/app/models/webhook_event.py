import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import WebhookProcessingStatus

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.commit import Commit


class WebhookEvent(BaseModel):
    __tablename__ = "webhook_events"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    delivery_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    processed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Rich processing state — supersedes the legacy boolean `processed` flag
    processing_status: Mapped[WebhookProcessingStatus] = mapped_column(
        Enum(WebhookProcessingStatus),
        nullable=False,
        default=WebhookProcessingStatus.RECEIVED,
        server_default=WebhookProcessingStatus.RECEIVED.value,
    )

    # Populated when processing_status transitions to PROCESSED or IGNORED
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Populated when processing_status transitions to FAILED
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        back_populates="webhook_events",
    )

    commits: Mapped[list["Commit"]] = relationship(
        back_populates="webhook_event",
        cascade="all, delete-orphan",
    )