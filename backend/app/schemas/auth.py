from pydantic import BaseModel, EmailStr


class TokenResponse(BaseModel):
    """Schema returning access and refresh JWT tokens to the client."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """Schema validating incoming token refresh requests."""
    refresh_token: str


class DemoLoginRequest(BaseModel):
    """Schema for demo email/password login (development only)."""
    email: str
    password: str

class LoginRequest(BaseModel):
    """Schema for production email/password login."""
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    """Schema for user registration."""
    full_name: str
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request."""
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    """Schema for reset password request."""
    token: str
    new_password: str
