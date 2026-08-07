import uuid
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from app.models.commit import Commit


class CommitQueryService:
    """
    Service responsible for querying commit details and loading related relationships.
    """
    def __init__(self, db: Session) -> None:
        """
        Initializes CommitQueryService with a database session.

        Args:
            db (Session): The synchronous SQLAlchemy database session.
        """
        self.db = db

    def get_commit_by_id(self, commit_id: uuid.UUID) -> Optional[Commit]:
        """
        Fetches commit details from the database using its UUID.

        Args:
            commit_id (uuid.UUID): The UUID of the commit.

        Returns:
            Optional[Commit]: The Commit model object if found, otherwise None.
        """
        return self.db.query(Commit).filter(Commit.id == commit_id).first()

    def get_commit_with_generations(self, commit_id: uuid.UUID) -> Optional[Commit]:
        """
        Fetches commit details along with related AIGeneration, CommitSummary, and Documentation
        records preloaded.

        Args:
            commit_id (uuid.UUID): The UUID of the commit.

        Returns:
            Optional[Commit]: The Commit model object with relations preloaded if found, otherwise None.
        """
        return (
            self.db.query(Commit)
            .options(
                joinedload(Commit.ai_generations),
                joinedload(Commit.summary),
                joinedload(Commit.documentation)
            )
            .filter(Commit.id == commit_id)
            .first()
        )

    def get_user_commit_with_generations(self, user_id: uuid.UUID, commit_id: uuid.UUID) -> Optional[Commit]:
        from app.models.repository import Repository
        return (
            self.db.query(Commit)
            .join(Repository, Commit.repository_id == Repository.id)
            .options(
                joinedload(Commit.ai_generations),
                joinedload(Commit.summary),
                joinedload(Commit.documentation)
            )
            .filter(Commit.id == commit_id, Repository.user_id == user_id)
            .first()
        )
