import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.repository import Repository


class RepositoryRepository:
    """
    Repository class handling direct database transactions for the Repository model.
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_repository(
        self,
        github_repo_id: int,
        owner: str,
        name: str,
        clone_url: str,
        default_branch: str = "main",
        webhook_enabled: bool = True,
        user_id: Optional[uuid.UUID] = None
    ) -> Repository:
        """
        Creates and persists a new Repository record.
        """
        repo = Repository(
            github_repo_id=github_repo_id,
            owner=owner,
            name=name,
            clone_url=clone_url,
            default_branch=default_branch,
            webhook_enabled=webhook_enabled,
            user_id=user_id
        )
        self.db.add(repo)
        self.db.commit()
        self.db.refresh(repo)
        return repo

    def get_by_id(self, repo_id: uuid.UUID) -> Optional[Repository]:
        """
        Retrieves a Repository record by its primary key ID.
        """
        return self.db.query(Repository).filter(Repository.id == repo_id).first()

    def get_by_github_repo_id(self, github_repo_id: int) -> Optional[Repository]:
        """
        Retrieves a Repository record by its unique GitHub Repository ID.
        """
        return self.db.query(Repository).filter(Repository.github_repo_id == github_repo_id).first()

    def get_by_user(self, user_id: uuid.UUID) -> List[Repository]:
        """
        Retrieves a list of Repository records belonging to a specific user.
        """
        return self.db.query(Repository).filter(Repository.user_id == user_id).all()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[Repository]:
        """
        Lists all Repository records with pagination (offset and limit).
        """
        return self.db.query(Repository).offset(skip).limit(limit).all()

    def update(self, repo_id: uuid.UUID, **kwargs) -> Repository:
        """
        Updates fields of an existing Repository record. Raises ValueError if not found.
        """
        repo = self.get_by_id(repo_id)
        if not repo:
            raise ValueError(f"Repository with ID {repo_id} not found.")

        for key, value in kwargs.items():
            if hasattr(repo, key):
                setattr(repo, key, value)

        self.db.commit()
        self.db.refresh(repo)
        return repo

    def delete(self, repo_id: uuid.UUID) -> bool:
        """
        Deletes a Repository record from the database. Raises ValueError if not found.
        """
        repo = self.get_by_id(repo_id)
        if not repo:
            raise ValueError(f"Repository with ID {repo_id} not found.")

        self.db.delete(repo)
        self.db.commit()
        return True

    def get_user_repository(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> Optional[Repository]:
        return self.db.query(Repository).filter(
            Repository.user_id == user_id,
            Repository.id == repository_id
        ).first()

    def get_user_repository_by_name(self, user_id: uuid.UUID, repo_name: str) -> Optional[Repository]:
        return self.db.query(Repository).filter(
            Repository.user_id == user_id,
            Repository.name == repo_name
        ).first()

    def update_user_repository(self, user_id: uuid.UUID, repository_id: uuid.UUID, **kwargs) -> Repository:
        repo = self.get_user_repository(user_id, repository_id)
        if not repo:
            raise ValueError("Repository not found or access denied.")
        for key, value in kwargs.items():
            if hasattr(repo, key):
                setattr(repo, key, value)
        self.db.commit()
        self.db.refresh(repo)
        return repo

    def delete_user_repository(self, user_id: uuid.UUID, repository_id: uuid.UUID) -> bool:
        repo = self.get_user_repository(user_id, repository_id)
        if not repo:
            raise ValueError("Repository not found or access denied.")
        self.db.delete(repo)
        self.db.commit()
        return True
