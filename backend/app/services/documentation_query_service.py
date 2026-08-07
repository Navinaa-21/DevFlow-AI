import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.models.documentation import Documentation


class DocumentationQueryService:
    """
    Service responsible for querying AI-generated technical documentation.
    """
    def __init__(self, db: Session) -> None:
        """
        Initializes DocumentationQueryService with a database session.

        Args:
            db (Session): The synchronous SQLAlchemy database session.
        """
        self.db = db

    def get_documentation_by_commit_id(self, commit_id: uuid.UUID) -> Optional[Documentation]:
        """
        Retrieves the generated documentation for a specific commit.

        Args:
            commit_id (uuid.UUID): The UUID of the commit.

        Returns:
            Optional[Documentation]: The Documentation model object if found, otherwise None.
        """
        return self.db.query(Documentation).filter(Documentation.commit_id == commit_id).first()

    def get_user_documentation_toc(self, user_id: uuid.UUID, limit: int = 20):
        from app.models.commit import Commit
        from app.models.repository import Repository
        from sqlalchemy import select
        
        stmt = (
            select(Documentation, Commit, Repository)
            .join(Commit, Documentation.commit_id == Commit.id)
            .join(Repository, Commit.repository_id == Repository.id)
            .where(Repository.user_id == user_id)
            .order_by(Documentation.created_at.desc())
            .limit(limit)
        )
        return self.db.execute(stmt).all()

    def get_user_documentation_by_commit_id(self, user_id: uuid.UUID, commit_id: uuid.UUID) -> Optional[Documentation]:
        from app.models.commit import Commit
        from app.models.repository import Repository
        return (
            self.db.query(Documentation)
            .join(Commit, Documentation.commit_id == Commit.id)
            .join(Repository, Commit.repository_id == Repository.id)
            .filter(Documentation.commit_id == commit_id, Repository.user_id == user_id)
            .first()
        )
