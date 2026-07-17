import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.enums import AuthProvider
from app.repositories.auth_repository import AuthRepository
from app.utils.oauth.registry import OAuthProviderRegistry, ProviderNotSupportedError
from app.utils.oauth.base import NormalizedProfile
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService


class AuthDomainError(Exception):
    """Base exception class for all Authentication domain errors."""
    pass


class AuthService:
    """Service class encapsulating business rules for User authentication and registration."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = AuthRepository(db)
        self.user_repo = UserRepository(db)

    async def get_login_redirect(self, provider_name: str, request: Any) -> Any:
        """Resolve redirect authorization RedirectResponse for the requested provider."""
        try:
            provider = OAuthProviderRegistry.get(provider_name)
            return await provider.get_redirect(request)
        except ProviderNotSupportedError as e:
            raise AuthDomainError(str(e))

    async def authenticate_oauth_callback(
        self,
        provider_name: str,
        code: str,
        request: Any
    ) -> User:
        """
        Orchestrates authentication callback:
        - Exchange authorization code for a normalized profile.
        - Resolve or link User in database.
        - Return the authenticated User model instance.
        """
        # 1. Resolve strategy provider
        try:
            provider_strategy = OAuthProviderRegistry.get(provider_name)
        except ProviderNotSupportedError as e:
            raise AuthDomainError(str(e))

        # 2. Exchange code for normalized profile details
        try:
            profile: NormalizedProfile = await provider_strategy.exchange_code_for_profile(code, request)
        except Exception as e:
            raise AuthDomainError(f"OAuth callback code exchange failed: {str(e)}")

        # Normalize email if present for canonical identity
        if profile.get("email"):
            profile["email"] = profile["email"].strip().lower()

        try:
            provider_enum = AuthProvider(provider_name.upper())
        except ValueError:
            raise AuthDomainError(f"Unsupported database authentication provider: {provider_name}")

        # 3. Check if OAuth account is already registered and mapped to a User
        oauth_account = self.repository.get_oauth_account(provider_enum, profile["provider_user_id"])
        if oauth_account:
            # Refresh credentials in the database
            oauth_account.access_token = profile.get("access_token")
            oauth_account.refresh_token = profile.get("refresh_token")
            oauth_account.expires_at = profile.get("expires_at")
            self.db.commit()
            self.db.refresh(oauth_account)
            
            user = self.db.get(User, oauth_account.user_id)
            if user:
                return user

        # 4. Fallback check: check if a User exists with the same verified email address
        if profile.get("email"):
            user = self.repository.get_user_by_email(profile["email"])
            if user:
                # Link OAuth account to this existing User record
                self.repository.link_oauth_account(
                    user_id=user.id,
                    provider=provider_enum,
                    provider_user_id=profile["provider_user_id"],
                    access_token=profile.get("access_token"),
                    refresh_token=profile.get("refresh_token"),
                    expires_at=profile.get("expires_at")
                )
                return user

        # 5. Create new User and link OAuthAccount atomically
        user = self.repository.create_user(
            full_name=profile["full_name"],
            email=profile.get("email") or "",
            avatar_url=profile["avatar_url"],
            is_verified=True  # OAuth verified account
        )
        
        self.repository.create_oauth_account(
            user_id=user.id,
            provider=provider_enum,
            provider_user_id=profile["provider_user_id"],
            access_token=profile.get("access_token"),
            refresh_token=profile.get("refresh_token"),
            expires_at=profile.get("expires_at")
        )
        
        # Automatically accept any pending workspace invitations for this new user
        from app.services.workspace_service import WorkspaceService
        ws_service = WorkspaceService(self.db)
        pending_invitations = ws_service.repository.get_all_pending_invitations_by_email(user.email)
        for invitation in pending_invitations:
            try:
                ws_service.accept_invitation(invitation.token, user)
            except Exception:
                pass  # Ignore errors like expired invitations
        
        return user

    def generate_auth_tokens(self, user: User) -> Dict[str, str]:
        """Generate Access and Refresh tokens for a User ORM instance."""
        if not user.is_active:
            raise AuthDomainError("User account is disabled.")
            
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }

    def demo_login(self, email: str, password: str) -> Dict[str, str]:
        """Demo-only login: validates hardcoded credentials and returns real JWT tokens."""
        DEMO_EMAIL = "demo@example.com"
        DEMO_PASSWORD = "demo123"

        email = email.strip().lower()

        if email != DEMO_EMAIL or password != DEMO_PASSWORD:
            raise AuthDomainError("Invalid demo credentials. Use demo@example.com / demo123.")

        # Get or create the demo user in the database
        user = self.repository.get_user_by_email(DEMO_EMAIL)
        if not user:
            user = self.repository.create_user(
                full_name="Demo User",
                email=DEMO_EMAIL,
                is_verified=True,
                is_active=True
            )

        return self.generate_auth_tokens(user)

    def refresh_auth_tokens(self, refresh_token: str) -> Dict[str, str]:
        """Verify a refresh token and return fresh access/refresh tokens."""
        try:
            claims = decode_token(refresh_token)
            if claims.get("type") != "refresh":
                raise AuthDomainError("Invalid token type claim.")
                
            user_id_str = claims.get("sub")
            if not user_id_str:
                raise AuthDomainError("Invalid subject claim.")
                
            user_id = UUID(user_id_str)
        except Exception as e:
            raise AuthDomainError(f"Invalid or expired refresh token: {str(e)}")

        # Fetch active user
        user = self.db.get(User, user_id)
        if not user or not user.is_active:
            raise AuthDomainError("Associated user account is disabled or does not exist.")

        return self.generate_auth_tokens(user)

    def register_user(self, full_name: str, email: str, password: str) -> Dict[str, str]:
        """Registers a new user via email/password and returns tokens."""
        email = email.strip().lower()
        if self.user_repo.email_exists(email):
            raise AuthDomainError("User with this email already exists.")
            
        hashed_pw = hash_password(password)
        user = self.user_repo.create_user(
            full_name=full_name,
            email=email,
            password_hash=hashed_pw
        )

        # Automatically accept any pending workspace invitations for this new user
        from app.services.workspace_service import WorkspaceService
        ws_service = WorkspaceService(self.db)
        pending_invitations = ws_service.repository.get_all_pending_invitations_by_email(user.email)
        for invitation in pending_invitations:
            try:
                ws_service.accept_invitation(invitation.token, user)
            except Exception:
                pass  # Ignore errors like expired invitations

        return self.generate_auth_tokens(user)
        
    def login_user(self, email: str, password: str) -> Dict[str, str]:
        """Authenticates an existing user and returns tokens."""
        email = email.strip().lower()
        user = self.user_repo.get_by_email(email)
        if not user:
            raise AuthDomainError("Invalid credentials.")
            
        if not user.password_hash:
            raise AuthDomainError("Account was created via a third-party provider (OAuth). Please log in with that provider.")
            
        if not verify_password(password, user.password_hash):
            raise AuthDomainError("Invalid credentials.")
            
        if not user.is_active:
            raise AuthDomainError("User account is disabled.")
            
        return self.generate_auth_tokens(user)

    def forgot_password(self, email: str) -> None:
        """Initiates the password reset flow by sending an email if the user exists."""
        email = email.strip().lower()
        user = self.user_repo.get_by_email(email)
        
        # Security: Return generic success even if user not found to prevent enumeration
        if not user or not user.is_active:
            return
            
        # Generate raw token and hash
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        
        self.repository.create_password_reset_token(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        
        email_service = EmailService()
        email_service.send_password_reset_email(user.email, raw_token)

    def reset_password(self, raw_token: str, new_password: str) -> None:
        """Validates token and resets the user's password."""
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        reset_token = self.repository.get_password_reset_token(token_hash)
        
        if not reset_token:
            raise AuthDomainError("Invalid or expired password reset token.")
            
        if reset_token.used_at is not None:
            raise AuthDomainError("Password reset token has already been used.")
            
        if datetime.now(timezone.utc) > reset_token.expires_at:
            raise AuthDomainError("Password reset token has expired.")
            
        user = self.db.get(User, reset_token.user_id)
        if not user or not user.is_active:
            raise AuthDomainError("Associated user account is disabled or does not exist.")
            
        user.password_hash = hash_password(new_password)
        reset_token.used_at = datetime.now(timezone.utc)
        
        self.db.commit()
