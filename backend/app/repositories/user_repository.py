from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.user import UserCreate, UserUpdate


class UserRepository(BaseRepository[User]):
    """Repository for handling database actions on the User model."""

    def __init__(self, db: Session):
        super().__init__(User, db)

    def get_by_email(self, email: str) -> Optional[User]:
        statement = select(User).where(User.email == email)
        return self.db.scalars(statement).first()

    def create(self, schema: UserCreate) -> User:
        user = User(
            full_name=schema.full_name,
            email=schema.email,
            avatar_url=schema.avatar_url,
            is_verified=schema.is_verified,
            is_active=schema.is_active,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, id: UUID, schema: UserUpdate) -> Optional[User]:
        user = self.get(id)
        if not user:
            return None
        
        update_data = schema.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)
            
        self.db.commit()
        self.db.refresh(user)
        return user

    def email_exists(self, email: str) -> bool:
        statement = select(User.id).where(User.email == email)
        return self.db.scalar(statement) is not None

    def create_user(
        self,
        full_name: str,
        email: str,
        password_hash: str,
    ) -> User:
        user = User(
            full_name=full_name,
            email=email,
            password_hash=password_hash,
            is_verified=False,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
