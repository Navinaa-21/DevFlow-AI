import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.commit import Commit


class CommitRepository:
    """
    Repository class handling direct database transactions for the Commit model.
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    def commit_exists(self, sha: str) -> bool:
        """
        Checks if a commit with the given SHA hash already exists in the database.
        """
        return self.db.query(Commit).filter(Commit.sha == sha).first() is not None

    def create_commit(
        self,
        repository_id: uuid.UUID,
        sha: str,
        message: str,
        author: str,
        committed_at: datetime
    ) -> Commit:
        """
        Creates and persists a new Commit. Raises a ValueError if a commit with the SHA already exists.
        """
        if self.commit_exists(sha):
            raise ValueError(f"Commit with SHA {sha} already exists.")

        commit_obj = Commit(
            repository_id=repository_id,
            sha=sha,
            message=message,
            author=author,
            committed_at=committed_at
        )
        self.db.add(commit_obj)
        self.db.commit()
        self.db.refresh(commit_obj)
        return commit_obj

    def get_by_sha(self, sha: str) -> Optional[Commit]:
        """
        Retrieves a Commit record by its SHA hash.
        """
        return self.db.query(Commit).filter(Commit.sha == sha).first()

    def get_by_repository(self, repository_id: uuid.UUID) -> List[Commit]:
        """
        Retrieves all Commit records linked to a specific repository.
        """
        return self.db.query(Commit).filter(Commit.repository_id == repository_id).all()

    def list_recent(self, limit: int = 20) -> List[Commit]:
        """
        Retrieves a list of the most recently committed Commits.
        """
        return self.db.query(Commit).order_by(Commit.committed_at.desc()).limit(limit).all()

    def get_user_commits(self, user_id: uuid.UUID, limit: int = 20) -> List[Commit]:
        from app.models.repository import Repository
        return self.db.query(Commit).join(Repository, Commit.repository_id == Repository.id).filter(
            Repository.user_id == user_id
        ).order_by(Commit.committed_at.desc()).limit(limit).all()
