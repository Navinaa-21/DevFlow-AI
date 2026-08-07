from typing import List, TYPE_CHECKING, Optional
import uuid
from sqlalchemy import String, BigInteger, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base_class import BaseModel

if TYPE_CHECKING:  #circular import
    from app.models.commit import Commit
    from app.models.user import User


class Repository(BaseModel):
    """
    SQLAlchemy model representing a monitored GitHub repository.
    """
    __tablename__ = "repositories"

    github_repo_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=True
    )
    owner: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    clone_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False
    )
    default_branch: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="main",
        server_default="main"
    )
    webhook_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )

    # Relationships
    commits: Mapped[List["Commit"]] = relationship(
        "Commit",
        back_populates="repository",
        cascade="all, delete-orphan" #Deleting the repository also deletes its associated commits
    )
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="repositories"
    )

