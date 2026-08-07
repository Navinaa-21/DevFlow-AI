# Import Base and BaseModel from base_class to make them available
from app.db.base_class import Base, BaseModel

# Import all model classes here to register with Base.metadata for Alembic migrations
from app.models.repository import Repository
from app.models.commit import Commit
from app.models.commit_summary import CommitSummary
from app.models.documentation import Documentation
from app.models.ai_generation import AIGeneration
from app.models.user import User
from app.models.oauth_account import OAuthAccount
