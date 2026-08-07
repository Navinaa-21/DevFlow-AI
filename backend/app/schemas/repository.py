from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class RepositoryCreate(BaseModel):
    name: str
    owner: str
    clone_url: str
    default_branch: str = "main"
    webhook_enabled: bool = True

class RepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    github_repo_id: int
    owner: str
    name: str
    clone_url: str
    default_branch: str
    webhook_enabled: bool
    created_at: datetime
    updated_at: datetime

class RepositoriesListResponse(BaseModel):
    repositories: List[RepositoryResponse]
    total_count: int
