from pydantic import BaseModel, EmailStr
from app.models.enums import WorkspaceRole


class InvitationCreate(BaseModel):
    """Schema validating incoming team invitation payloads."""
    email: EmailStr
    role: WorkspaceRole
