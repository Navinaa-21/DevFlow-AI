import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.ai_generation import AIGeneration


class AIGenerationRepository:
    """
    Repository class handling direct database transactions for the AIGeneration model.
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_generation(self, commit_id: uuid.UUID, provider: str, status: str = "pending") -> AIGeneration:
        """
        Creates and persists a new AIGeneration tracker log.
        """
        gen_obj = AIGeneration(
            commit_id=commit_id,
            provider=provider,
            status=status
        )
        self.db.add(gen_obj)
        self.db.commit()
        self.db.refresh(gen_obj)
        return gen_obj

    def update_status(self, generation_id: uuid.UUID, status: str) -> AIGeneration:
        """
        Updates the status of an existing AIGeneration request. Raises ValueError if not found.
        """
        gen_obj = self.db.query(AIGeneration).filter(AIGeneration.id == generation_id).first()
        if not gen_obj:
            raise ValueError(f"AIGeneration record with ID {generation_id} not found.")

        gen_obj.status = status
        self.db.commit()
        self.db.refresh(gen_obj)
        return gen_obj

    def get_by_commit(self, commit_id: uuid.UUID) -> List[AIGeneration]:
        """
        Retrieves all AIGeneration logs associated with a specific commit_id.
        """
        return self.db.query(AIGeneration).filter(AIGeneration.commit_id == commit_id).all()

    def list_pending(self, limit: int = 100) -> List[AIGeneration]:
        """
        Retrieves all AIGeneration records that are currently in a "pending" status.
        """
        return self.db.query(AIGeneration).filter(AIGeneration.status == "pending").limit(limit).all()
