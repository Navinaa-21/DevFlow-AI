import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import BaseModel

if TYPE_CHECKING:
    from app.models.commit import Commit


class Documentation(BaseModel):
    """
    SQLAlchemy model representing the AI-generated documentation update for a specific commit.
    """
    __tablename__ = "documentations"

    commit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("commits.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    markdown: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # Relationships
    commit: Mapped["Commit"] = relationship(
        "Commit",
        back_populates="documentation"
    )
