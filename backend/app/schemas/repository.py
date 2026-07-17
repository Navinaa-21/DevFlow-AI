import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter, field_validator

from app.models.enums import RepositoryProvider


class RepositoryCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    provider: RepositoryProvider = Field(..., description="The external hosting provider")
    provider_repository_id: str = Field(..., min_length=1, max_length=255)
    clone_url: str = Field(..., min_length=1, max_length=500)
    default_branch: str = Field("main", max_length=100)
    visibility: str = Field("private", max_length=50)

    @field_validator("clone_url")
    @classmethod
    def validate_clone_url(cls, value: str) -> str:
        trimmed = value.strip()
        TypeAdapter(HttpUrl).validate_python(trimmed)
        return trimmed

    @field_validator("name", "provider_repository_id", "default_branch", "visibility")
    @classmethod
    def trim_strings(cls, value: str) -> str:
        return value.strip()


class RepositoryUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    default_branch: Optional[str] = Field(None, max_length=100)
    visibility: Optional[str] = Field(None, max_length=50)

    @field_validator("name", "default_branch", "visibility")
    @classmethod
    def trim_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip()


class ExternalRepositoryResponse(BaseModel):
    """Represents a repository fetched directly from an external provider (like GitHub API)."""

    provider_repo_id: str = Field(..., description="The unique ID of the repository on the external provider")
    provider: RepositoryProvider = Field(..., description="The external hosting provider (e.g. GITHUB)")
    name: str = Field(..., max_length=255, description="Short name of the repository")
    full_name: str = Field(..., max_length=255, description="Full repository owner/name path")
    repo_url: str = Field(..., max_length=500, description="Web URL of the repository")
    default_branch: str = Field("main", max_length=100, description="The default branch name")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description of the repository")
    private: bool = Field(False, description="Whether the repository is private or public")

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, value: str) -> str:
        trimmed = value.strip()
        TypeAdapter(HttpUrl).validate_python(trimmed)
        return trimmed

    @field_validator("provider_repo_id", "name", "full_name", "default_branch")
    @classmethod
    def trim_strings(cls, value: str) -> str:
        return value.strip()


class RepositoryConnectRequest(BaseModel):
    """Payload containing list of provider repository IDs to connect to a workspace."""

    repository_ids: List[str] = Field(..., description="List of provider repository IDs to link")

    @field_validator("repository_ids")
    @classmethod
    def validate_ids(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("Repository IDs list cannot be empty.")

        if len(value) > 100:
            raise ValueError("Cannot connect more than 100 repositories in a single request.")

        trimmed_ids = [item.strip() for item in value if item.strip()]
        if not trimmed_ids:
            raise ValueError("Repository IDs list must contain non-empty/non-whitespace strings.")

        if len(trimmed_ids) != len(set(trimmed_ids)):
            raise ValueError("Duplicate repository IDs are not allowed in the request.")

        return trimmed_ids


class RepositoryResponse(BaseModel):
    """Response representing a repository stored in our database."""

    id: uuid.UUID
    workspace_id: uuid.UUID
    provider: RepositoryProvider
    provider_repo_id: str
    name: str
    full_name: Optional[str] = None
    repo_url: Optional[str] = None
    clone_url: Optional[str] = None
    default_branch: str
    visibility: str
    last_synced_at: Optional[datetime] = None
    webhook_enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RepositoryListResponse(BaseModel):
    """Paginated list of stored repositories."""

    items: List[RepositoryResponse]
    total: int = Field(..., ge=0)
    limit: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)

    model_config = ConfigDict(from_attributes=True)
