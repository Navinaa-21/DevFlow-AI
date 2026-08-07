from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class GitUser(BaseModel):
    """
    Schema for commit author/committer.
    """
    name: str
    email: str
    username: Optional[str] = None


class GitCommit(BaseModel):
    """
    Schema representing an individual commit in the webhook payload.
    """
    id: str = Field(..., description="The SHA of the commit")
    message: str
    timestamp: str
    author: GitUser
    committer: GitUser
    added: List[str] = Field(default_factory=list)
    removed: List[str] = Field(default_factory=list)
    modified: List[str] = Field(default_factory=list)


class GitRepository(BaseModel):
    """
    Schema representing the repository details in the webhook payload.
    """
    id: int
    name: str
    full_name: str
    html_url: str
    clone_url: str


class WebhookPayload(BaseModel):
    """
    Root schema for an incoming Git/GitHub webhook event payload.
    """
    ref: str
    before: str
    after: str
    repository: GitRepository
    commits: List[GitCommit] = Field(default_factory=list)
    compare: Optional[str] = None
