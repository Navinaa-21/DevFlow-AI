from typing import Optional, Sequence
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Service class encapsulating business rules for User management."""

    def __init__(self, db: Session):
        self.repository = UserRepository(db)

    def create_user(self, schema: UserCreate) -> User:
        existing_user = self.repository.get_by_email(schema.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists."
            )
        return self.repository.create(schema)

    def get_user_by_id(self, id: UUID) -> User:
        user = self.repository.get(id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        return user

    def get_user_by_email(self, email: str) -> User:
        user = self.repository.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        return user

    def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[dict] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> Sequence[User]:
        return self.repository.list(
            skip=skip,
            limit=limit,
            filters=filters,
            search=search,
            search_fields=["full_name", "email"],
            sort_by=sort_by,
        )

    def update_user(self, id: UUID, schema: UserUpdate) -> User:
        if schema.email is not None:
            existing_user = self.repository.get_by_email(schema.email)
            if existing_user and existing_user.id != id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A user with this email already exists."
                )
                
        user = self.repository.update(id, schema)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
        return user

    def delete_user(self, id: UUID) -> None:
        success = self.repository.delete(id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )
