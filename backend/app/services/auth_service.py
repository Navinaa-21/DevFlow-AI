from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.repositories.auth_repository import AuthRepository
from app.models.user import User

class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.auth_repo = AuthRepository(db)

    def handle_github_login(self, profile: dict, access_token: str) -> User:
        """
        Handles the business logic for GitHub login/signup.
        Expects a GitHub profile dict.
        """
        provider_account_id = str(profile.get("id"))
        email = profile.get("email")
        name = profile.get("name")
        avatar_url = profile.get("avatar_url")
        username = profile.get("login")
        
        if not provider_account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid GitHub profile: missing ID."
            )
            
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GitHub account must have an email associated."
            )
            
        # 1. Check if OAuth account exists
        oauth_account = self.auth_repo.get_oauth_account(
            provider="github",
            provider_account_id=provider_account_id
        )
        
        if oauth_account:
            # Update access token if changed
            if oauth_account.access_token != access_token:
                self.auth_repo.update_oauth_account(
                    account_id=oauth_account.id,
                    access_token=access_token
                )
            
            # Update user profile if changed
            user = oauth_account.user
            self.auth_repo.update_user(
                user_id=user.id,
                name=name,
                avatar_url=avatar_url,
                username=username
            )
            return user
            
        # 2. Check if user with email already exists
        user = self.auth_repo.get_user_by_email(email)
            
        if not user:
            # Create a new user
            user = self.auth_repo.create_user(
                email=email,
                is_active=True
            )
            # Update additional profile fields
            self.auth_repo.update_user(
                user_id=user.id,
                name=name,
                avatar_url=avatar_url,
                username=username
            )
            
        # 3. Create OAuth account and link it
        self.auth_repo.create_oauth_account(
            user_id=user.id,
            provider="github",
            provider_account_id=provider_account_id,
            access_token=access_token
        )
        
        return user
