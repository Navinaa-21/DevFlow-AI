import uuid
import re
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict, TypeAdapter

# Regex: Only lowercase alphanumeric characters and single hyphens (no leading/trailing hyphens)
SLUG_REGEX = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class WorkspaceBase(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="The name of the workspace",
        examples=["My Tech Startup"]
    )
    slug: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="A URL-friendly unique identifier (lowercase alphanumeric and single hyphens)",
        examples=["my-tech-startup"]
    )
    logo_url: Optional[str] = Field(
        None,
        description="URL pointing to the workspace's logo image",
        examples=["https://example.com/logo.png"]
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="A brief description of the workspace",
        examples=["Workspace for collaboration on software engineering projects."]
    )
    is_active: bool = Field(
        True,
        description="Whether the workspace is active or deactivated"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Workspace name cannot be empty or contain only whitespace.")
        return trimmed

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        trimmed = v.strip().lower()
        if not trimmed:
            raise ValueError("Workspace slug cannot be empty or contain only whitespace.")
        if not SLUG_REGEX.match(trimmed):
            raise ValueError(
                "Workspace slug must contain only lowercase alphanumeric characters and single hyphens, "
                "and cannot start or end with a hyphen."
            )
        return trimmed

    @field_validator("logo_url")
    @classmethod
    def validate_logo_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_str = str(v).strip()
            if not v_str:
                return None
            try:
                TypeAdapter(HttpUrl).validate_python(v_str)
            except Exception:
                raise ValueError("logo_url must be a valid HTTP or HTTPS URL.")
            return v_str
        return None

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            return trimmed if trimmed else None
        return None


class WorkspaceCreate(WorkspaceBase):
    owner_id: uuid.UUID = Field(
        ...,
        description="The UUID of the user who owns and creates the workspace"
    )


class UpdateWorkspaceRequest(BaseModel):
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="The updated name of the workspace",
        examples=["New Team Name"]
    )
    slug: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="The updated URL-friendly unique identifier",
        examples=["new-team-name"]
    )
    description: Optional[str] = Field(
        None,
        max_length=1000,
        description="The updated description of the workspace"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Workspace name cannot be empty.")
            return trimmed
        return None

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip().lower()
            if not trimmed:
                raise ValueError("Workspace slug cannot be empty.")
            if not SLUG_REGEX.match(trimmed):
                raise ValueError(
                    "Workspace slug must contain only lowercase alphanumeric characters and single hyphens, "
                    "and cannot start or end with a hyphen."
                )
            return trimmed
        return None

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            return trimmed if trimmed else None
        return None


class WorkspaceUpdate(UpdateWorkspaceRequest):
    pass


class TransferOwnershipRequest(BaseModel):
    new_owner_id: uuid.UUID = Field(
        ...,
        description="The UUID of the workspace member that should become the new owner",
    )


class WorkspaceResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    logo_url: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "My Tech Startup",
                "slug": "my-tech-startup",
                "logo_url": "https://example.com/logo.png",
                "description": "Workspace for collaboration on software engineering projects.",
                "is_active": True,
                "created_at": "2026-07-13T10:00:00Z",
                "updated_at": "2026-07-13T10:00:00Z"
            }
        }
    )


class WorkspaceListResponse(BaseModel):
    items: List[WorkspaceResponse] = Field(..., description="The list of workspace records")
    total: int = Field(..., description="The total number of workspaces matching query filters")
    limit: int = Field(..., description="The maximum number of items returned in this page")
    offset: int = Field(..., description="The index starting point for the pagination")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "name": "My Tech Startup",
                        "slug": "my-tech-startup",
                        "logo_url": "https://example.com/logo.png",
                        "description": "Workspace description",
                        "is_active": True,
                        "created_at": "2026-07-13T10:00:00Z",
                        "updated_at": "2026-07-13T10:00:00Z"
                    }
                ],
                "total": 1,
                "limit": 10,
                "offset": 0
            }
        }
    )


class WorkspaceCreateRequest(WorkspaceBase):
    """Schema for incoming API requests where the owner_id is derived from the JWT."""
    pass


class WorkspaceMemberResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    role: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "full_name": "Jane Doe",
                "email": "jane@example.com",
                "role": "owner"
            }
        }
    )
