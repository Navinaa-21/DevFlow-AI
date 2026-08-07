from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class UserResponse(BaseModel):
    id: UUID
    email: str
    is_active: bool
    created_at: datetime
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    username: Optional[str] = None
    provider: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None

class TokenPayload(BaseModel):
    sub: str
    exp: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class OAuthCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None
