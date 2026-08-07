import uuid
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import BaseModel

if TYPE_CHECKING:
    from app.models.commit import Commit


class AIGeneration(BaseModel):
    """
    SQLAlchemy model representing an AI generation request/status.
    """
    __tablename__ = "ai_generations"

    commit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commits.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        server_default="pending"
    )

    # Relationships
    commit: Mapped["Commit"] = relationship(
        "Commit",
        back_populates="ai_generations"
    )
