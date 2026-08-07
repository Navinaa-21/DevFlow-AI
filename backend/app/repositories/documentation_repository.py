import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.models.documentation import Documentation


class DocumentationRepository:
    """
    Repository class handling direct database transactions for the Documentation model.
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_documentation(self, commit_id: uuid.UUID, markdown: str) -> Documentation:
        """
        Creates and persists a new Documentation record. Since commit_id has a unique constraint,
        attempting to create multiple records for the same commit_id will fail.
        """
        doc_obj = Documentation(
            commit_id=commit_id,
            markdown=markdown
        )
        self.db.add(doc_obj)
        self.db.commit()
        self.db.refresh(doc_obj)
        return doc_obj

    def get_by_commit(self, commit_id: uuid.UUID) -> Optional[Documentation]:
        """
        Retrieves the Documentation record associated with a specific commit_id.
        """
        return self.db.query(Documentation).filter(Documentation.commit_id == commit_id).first()
