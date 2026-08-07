import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.repository import Repository
from app.models.commit import Commit
from app.models.ai_generation import AIGeneration
from app.models.documentation import Documentation

class DashboardRepository:
    """
    Repository class handling dashboard queries restricted by user ownership.
    """
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_dashboard(self, user_id: uuid.UUID) -> dict:
        repo_count = self.db.query(func.count(Repository.id)).filter(
            Repository.user_id == user_id
        ).scalar() or 0
        
        commit_count = self.db.query(func.count(Commit.id)).join(
            Repository, Commit.repository_id == Repository.id
        ).filter(Repository.user_id == user_id).scalar() or 0
        
        ai_models_count = self.db.query(func.count(func.distinct(AIGeneration.provider))).join(
            Commit, AIGeneration.commit_id == Commit.id
        ).join(
            Repository, Commit.repository_id == Repository.id
        ).filter(Repository.user_id == user_id).scalar() or 0
        
        docs_count = self.db.query(func.count(Documentation.id)).join(
            Commit, Documentation.commit_id == Commit.id
        ).join(
            Repository, Commit.repository_id == Repository.id
        ).filter(Repository.user_id == user_id).scalar() or 0
        
        return {
            "total_repositories": repo_count,
            "total_commits_processed": commit_count,
            "active_ai_models": ai_models_count,
            "documentation_pages": docs_count
        }
