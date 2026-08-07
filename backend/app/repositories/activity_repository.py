import uuid
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.repository import Repository
from app.models.commit import Commit
from app.models.ai_generation import AIGeneration
from app.schemas.activity import ActivityItemResponse

class ActivityRepository:
    """
    Repository class handling activity queries restricted by user ownership.
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_activity(self, user_id: uuid.UUID, limit: int = 20) -> List[ActivityItemResponse]:
        stmt = (
            select(AIGeneration, Commit, Repository)
            .join(Commit, AIGeneration.commit_id == Commit.id)
            .join(Repository, Commit.repository_id == Repository.id)
            .where(Repository.user_id == user_id)
            .order_by(AIGeneration.created_at.desc())
            .limit(limit)
        )
        results = self.db.execute(stmt).all()
        
        activities = []
        for ai_gen, commit, repo in results:
            activities.append(ActivityItemResponse(
                event=f"AI Analysis - {ai_gen.provider}",
                repo=f"{repo.owner}/{repo.name}",
                details=f"Analyzed commit {commit.sha[:7]}: {commit.message}",
                time=ai_gen.created_at,
                status=ai_gen.status
            ))
            
        return activities
