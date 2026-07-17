from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import List, Optional


class RepositoryStatsResponse(BaseModel):
    total_repositories: int = Field(..., description="Total repositories connected")
    active_repositories: int = Field(..., description="Active repositories count")
    archived_repositories: int = Field(..., description="Archived repositories count")
    total_commits: int = Field(..., description="Total commit count across repositories")
    commits_last_24h: int = Field(..., description="Commits within the last 24 hours")
    commits_last_7d: int = Field(..., description="Commits within the last 7 days")
    last_sync_time: Optional[datetime] = Field(None, description="Most recent repository synchronization time")

    model_config = ConfigDict(from_attributes=True)


class DashboardSummaryResponse(BaseModel):
    total_workspaces: int = Field(..., description="Total workspaces user belongs to")
    repositories: RepositoryStatsResponse = Field(..., description="Aggregate repository and commit metrics")

    model_config = ConfigDict(from_attributes=True)


class RecentActivityResponse(BaseModel):
    id: UUID = Field(..., description="Commit UUID")
    repository_id: UUID = Field(..., description="Repository UUID")
    repository_name: str = Field(..., description="Repository short name")
    commit_sha: str = Field(..., description="Commit full SHA")
    short_sha: str = Field(..., description="Commit short SHA")
    commit_message: str = Field(..., description="Commit message")
    committed_at: datetime = Field(..., description="Commit timestamp")
    author_name: str = Field(..., description="Author's name")
    author_email: str = Field(..., description="Author's email")
    branch: str = Field(..., description="Commit target branch")

    model_config = ConfigDict(from_attributes=True)


class WorkspaceSummaryResponse(BaseModel):
    id: UUID = Field(..., description="Workspace UUID")
    name: str = Field(..., description="Workspace name")
    slug: str = Field(..., description="Workspace slug")
    description: Optional[str] = Field(None, description="Workspace description")
    repository_count: int = Field(..., description="Total repositories connected to this workspace")
    active_repository_count: int = Field(..., description="Active repositories connected to this workspace")
    archived_repository_count: int = Field(..., description="Archived repositories connected to this workspace")
    total_commits: int = Field(..., description="Total commits across all repos in this workspace")
    last_synced_at: Optional[datetime] = Field(None, description="Most recent sync timestamp in this workspace")

    model_config = ConfigDict(from_attributes=True)
