import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import BaseModel

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.commit_summary import CommitSummary
    from app.models.documentation import Documentation
    from app.models.ai_generation import AIGeneration

class Commit(BaseModel):
    """
    SQLAlchemy model representing a Git commit associated with a repository.
    """
    __tablename__ = "commits"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sha: Mapped[str] = mapped_column(  #This is Git's unique identifier for a commit.
        String(40),
        unique=True,
        nullable=False,
        index=True
    )
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    author: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(
        "Repository",
        back_populates="commits"
    )
    summary: Mapped[Optional["CommitSummary"]] = relationship(
        "CommitSummary",
        back_populates="commit",
        uselist=False,
        cascade="all, delete-orphan"
    )
    documentation: Mapped[Optional["Documentation"]] = relationship(
        "Documentation",
        back_populates="commit",
        uselist=False,
        cascade="all, delete-orphan"
    )
    ai_generations: Mapped[List["AIGeneration"]] = relationship(
        "AIGeneration",
        back_populates="commit",
        cascade="all, delete-orphan"
    )



