import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.models.commit_summary import CommitSummary


class CommitSummaryRepository:
    """
    Repository class handling direct database transactions for the CommitSummary model.
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_summary(self, commit_id: uuid.UUID, summary_text: str) -> CommitSummary:
        """
        Creates and persists a new CommitSummary. If one already exists for the commit_id,
        it will raise an IntegrityError or duplicate error since commit_id has a unique constraint.
        """
        summary_obj = CommitSummary(
            commit_id=commit_id,
            summary=summary_text
        )
        self.db.add(summary_obj)
        self.db.commit()
        self.db.refresh(summary_obj)
        return summary_obj

    def get_by_commit(self, commit_id: uuid.UUID) -> Optional[CommitSummary]:
        """
        Retrieves the CommitSummary associated with a specific commit_id.
        """
        return self.db.query(CommitSummary).filter(CommitSummary.commit_id == commit_id).first()
