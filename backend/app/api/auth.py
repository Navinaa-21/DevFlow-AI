from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.schemas.auth import TokenResponse, TokenRefreshRequest, DemoLoginRequest, LoginRequest, RegisterRequest
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService, AuthDomainError
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Registers a new user using email and password, returning JWT tokens upon success.",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        return service.register_user(payload.full_name, payload.email, payload.password)
    except AuthDomainError as e:
        if "already exists" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
    description="Authenticates a user and returns real JWT tokens.",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        return service.login_user(payload.email, payload.password)
    except AuthDomainError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post(
    "/login/demo",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Demo login with email and password",
    description="Development-only endpoint. Accepts hardcoded demo credentials and returns real JWT tokens.",
)
def login_demo(payload: DemoLoginRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        return service.demo_login(payload.email, payload.password)
    except AuthDomainError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest

@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Request a password reset",
    description="Sends a password reset email if the account exists. Always returns a generic success response.",
)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    service.forgot_password(payload.email)
    # Always return a generic response to prevent email enumeration
    return {"message": "If an account with that email exists, we have sent a password reset link."}

@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset password",
    description="Validates the reset token and updates the user's password.",
)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    try:
        service.reset_password(payload.token, payload.new_password)
        return {"message": "Password successfully updated."}
    except AuthDomainError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/login/{provider}",
    summary="Initiate OAuth login flow",
    description="Redirects the client browser to the requested third-party provider authorization consent screen.",
)
async def login_oauth(provider: str, request: Request, db: Session = Depends(get_db)):
    service = AuthService(db)
    # This returns an Authlib RedirectResponse directly to the browser
    return await service.get_login_redirect(provider, request)


import urllib.parse

@router.get(
    "/callback/{provider}",
    summary="OAuth callback handler",
    description="Handles the callback redirect from the OAuth provider, exchanges the code, links or creates the User, and redirects to frontend with JWT tokens.",
)
async def oauth_callback(
    provider: str,
    code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    service = AuthService(db)
    user = await service.authenticate_oauth_callback(provider, code, request)
    tokens = service.generate_auth_tokens(user)
    
    query_params = urllib.parse.urlencode({
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"]
    })
    
    frontend_url = f"{settings.FRONTEND_URL}/auth/callback?{query_params}"
    return RedirectResponse(url=frontend_url)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access tokens",
    description="Provide a valid Refresh Token to receive a new pair of Access and Refresh tokens.",
)
def refresh_token(payload: TokenRefreshRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    return service.refresh_auth_tokens(payload.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user details",
    description="Retrieve account profile details of the currently authenticated User.",
)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user session",
    description="Stateless token logout. Instructs the client browser/application to discard token state.",
)
def logout(current_user: User = Depends(get_current_user)):
    # Since JWT is stateless, server side logout is a no-op (204 response).
    # Client should discard their tokens.
    return None
