from datetime import datetime
from uuid import UUID
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class CommitSummaryResponse(BaseModel):
    """
    Pydantic schema representing the generated summary response.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    commit_id: UUID
    summary: str
    created_at: datetime


class DocumentationResponse(BaseModel):
    """
    Pydantic schema representing the generated documentation response.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    commit_id: UUID
    markdown: str
    created_at: datetime


class AIGenerationResponse(BaseModel):
    """
    Pydantic schema representing the AI generation metadata/logs response.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    commit_id: UUID
    provider: str
    status: str
    created_at: datetime


class CommitResponse(BaseModel):
    """
    Pydantic schema for detailed Commit responses, including nested entities.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sha: str
    message: str
    author: Optional[str] = None
    repository_id: UUID
    committed_at: datetime
    created_at: datetime
    
    # Optional nested relationships
    summary: Optional[CommitSummaryResponse] = None
    documentation: Optional[DocumentationResponse] = None
    ai_generations: List[AIGenerationResponse] = []
