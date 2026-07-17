from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import RepositoryProvider
from app.models.repository import Repository
from app.repositories.base import BaseRepository


class RepositoryRepository(BaseRepository[Repository]):
    """Persistence-only repository for workspace repository records."""

    def __init__(self, db: Session):
        super().__init__(Repository, db)

    def create_repository(self, **fields) -> Repository:
        repository = Repository(**fields)
        self.db.add(repository)
        self.db.commit()
        self.db.refresh(repository)
        return repository

    def get_repository_by_id(self, repository_id: UUID) -> Optional[Repository]:
        return self.db.get(Repository, repository_id)

    def get_repository_by_provider_id(self, provider: RepositoryProvider, provider_repository_id: str) -> Optional[Repository]:
        statement = select(Repository).where(
            Repository.provider == provider,
            Repository.provider_repo_id == provider_repository_id,
        )
        return self.db.scalars(statement).first()

    def list_workspace_repositories(self, workspace_id: UUID) -> Sequence[Repository]:
        statement = select(Repository).where(Repository.workspace_id == workspace_id)
        return self.db.scalars(statement).all()

    def update_repository(self, repository_id: UUID, **fields) -> Optional[Repository]:
        repository = self.get_repository_by_id(repository_id)
        if not repository:
            return None

        for key, value in fields.items():
            if value is not None:
                setattr(repository, key, value)

        self.db.commit()
        self.db.refresh(repository)
        return repository

    def delete_repository(self, repository_id: UUID) -> bool:
        repository = self.get_repository_by_id(repository_id)
        if not repository:
            return False

        self.db.delete(repository)
        self.db.commit()
        return True

    def repository_exists(self, provider: RepositoryProvider, provider_repository_id: str) -> bool:
        statement = select(Repository.id).where(
            Repository.provider == provider,
            Repository.provider_repo_id == provider_repository_id,
        )
        return self.db.scalar(statement) is not None
