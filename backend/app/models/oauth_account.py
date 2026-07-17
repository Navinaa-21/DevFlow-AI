import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import AuthProvider

if TYPE_CHECKING:
    from app.models.user import User


class OAuthAccount(BaseModel):
    __tablename__ = "oauth_accounts"

    __table_args__ = (
        UniqueConstraint(
            "provider",
            "provider_user_id",
            name="uq_provider_user_id",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    provider: Mapped[AuthProvider] = mapped_column(
        Enum(AuthProvider),
        nullable=False,
    )

    provider_user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    access_token: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )

    refresh_token: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )

    expires_at: Mapped[Optional[datetime]] = mapped_column(
        nullable=True,
    )

    user: Mapped["User"] = relationship(
        back_populates="oauth_accounts",
    )