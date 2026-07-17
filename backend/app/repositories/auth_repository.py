from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.oauth_account import OAuthAccount
from app.models.password_reset_token import PasswordResetToken
from app.models.enums import AuthProvider
from app.repositories.base import BaseRepository


class AuthRepository(BaseRepository[OAuthAccount]):
    """Repository handling database access for User authentication and OAuth accounts."""

    def __init__(self, db: Session):
        super().__init__(OAuthAccount, db)

    def get_oauth_account(self, provider: AuthProvider, provider_user_id: str) -> Optional[OAuthAccount]:
        """Fetch an OAuthAccount record by provider and provider-specific user ID."""
        statement = select(OAuthAccount).where(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_user_id == provider_user_id
        )
        return self.db.scalars(statement).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Fetch a User record by their email address."""
        statement = select(User).where(User.email == email)
        return self.db.scalars(statement).first()

    def get_user_by_oauth(self, provider: AuthProvider, provider_user_id: str) -> Optional[User]:
        """Fetch the User linked to a specific OAuth account using a JOIN query."""
        statement = (
            select(User)
            .join(OAuthAccount, User.id == OAuthAccount.user_id)
            .where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id
            )
        )
        return self.db.scalars(statement).first()

    def create_user(
        self,
        full_name: str,
        email: str,
        avatar_url: Optional[str] = None,
        is_verified: bool = False,
        is_active: bool = True
    ) -> User:
        """Create a new User record in the database."""
        user = User(
            full_name=full_name,
            email=email,
            avatar_url=avatar_url,
            is_verified=is_verified,
            is_active=is_active
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_oauth_account(
        self,
        user_id: UUID,
        provider: AuthProvider,
        provider_user_id: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> OAuthAccount:
        """Create a new OAuthAccount record linked to a User UUID."""
        oauth_account = OAuthAccount(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )
        self.db.add(oauth_account)
        self.db.commit()
        self.db.refresh(oauth_account)
        return oauth_account

    def link_oauth_account(
        self,
        user_id: UUID,
        provider: AuthProvider,
        provider_user_id: str,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> OAuthAccount:
        """Link an OAuthAccount to an existing User (creates the OAuthAccount mapping record)."""
        return self.create_oauth_account(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )

    def create_password_reset_token(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime
    ) -> PasswordResetToken:
        """Create a new PasswordResetToken record."""
        token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_password_reset_token(self, token_hash: str) -> Optional[PasswordResetToken]:
        """Fetch a PasswordResetToken by its hash."""
        statement = select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        return self.db.scalars(statement).first()
