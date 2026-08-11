import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.oauth_account import OAuthAccount
from app.core.security_encryption import get_encryption_service

class AuthRepository:
    """
    Repository class handling direct database transactions for User and OAuthAccount models.
    """
    def __init__(self, db: Session) -> None:
        self.db = db
        self.encryption_service = get_encryption_service()

    # User operations
    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def create_user(self, email: str, hashed_password: Optional[str] = None, is_active: bool = True) -> User:
        user = User(
            email=email,
            hashed_password=hashed_password,
            is_active=is_active
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user_id: uuid.UUID, **kwargs) -> User:
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found.")

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    # OAuthAccount operations
    def get_oauth_account(self, provider: str, provider_account_id: str) -> Optional[OAuthAccount]:
        return self.db.query(OAuthAccount).filter(
            OAuthAccount.provider == provider,
            OAuthAccount.provider_account_id == provider_account_id
        ).first()

    def create_oauth_account(
        self, 
        user_id: uuid.UUID, 
        provider: str, 
        provider_account_id: str, 
        access_token: str, 
        refresh_token: Optional[str] = None
    ) -> OAuthAccount:
        encrypted_access_token = self.encryption_service.encrypt_token(access_token)
        encrypted_refresh_token = self.encryption_service.encrypt_token(refresh_token) if refresh_token else None
        
        oauth_account = OAuthAccount(
            user_id=user_id,
            provider=provider,
            provider_account_id=provider_account_id,
            access_token=encrypted_access_token,
            refresh_token=encrypted_refresh_token
        )
        self.db.add(oauth_account)
        self.db.commit()
        self.db.refresh(oauth_account)
        return oauth_account

    def update_oauth_account(self, account_id: uuid.UUID, **kwargs) -> OAuthAccount:
        account = self.db.query(OAuthAccount).filter(OAuthAccount.id == account_id).first()
        if not account:
            raise ValueError(f"OAuthAccount with ID {account_id} not found.")

        if "access_token" in kwargs and kwargs["access_token"]:
            kwargs["access_token"] = self.encryption_service.encrypt_token(kwargs["access_token"])
        if "refresh_token" in kwargs and kwargs["refresh_token"]:
            kwargs["refresh_token"] = self.encryption_service.encrypt_token(kwargs["refresh_token"])

        for key, value in kwargs.items():
            if hasattr(account, key):
                setattr(account, key, value)

        self.db.commit()
        self.db.refresh(account)
        return account

