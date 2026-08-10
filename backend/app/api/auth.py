from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.utils.oauth import oauth
from app.services.auth_service import AuthService
from app.core.security import create_access_token, get_current_user
from app.schemas.auth import UserResponse
from app.core.config import settings

router = APIRouter()

@router.get("/github/login")
async def github_login(request: Request):
    """
    Redirects the user to the GitHub OAuth login page.
    """
    # If accessing via 127.0.0.1, redirect to localhost so that the session cookie matches
    # the registered GitHub OAuth callback domain (localhost:8000)
    if "127.0.0.1" in str(request.base_url):
        new_url = str(request.url).replace("127.0.0.1", "localhost")
        return RedirectResponse(url=new_url)

    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/api/v1/auth/github/callback"
    return await oauth.github.authorize_redirect(request, redirect_uri)

@router.get("/github/callback")
async def github_callback(request: Request, db: Session = Depends(get_db)):
    """
    Handles the callback from GitHub OAuth, fetches profile, and returns a JWT.
    """
    try:
        token = await oauth.github.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback failed: {str(e)}"
        )
        
    access_token = token.get('access_token')
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to retrieve access token from GitHub."
        )

    # Fetch user profile using the access token
    resp = await oauth.github.get('user', token=token)
    profile = resp.json()
    
    # Email might not be in the primary profile response if private, 
    # but we assume scope user:email covers it or we could make a secondary request.
    if not profile.get("email"):
        # Make a secondary request to get emails
        emails_resp = await oauth.github.get('user/emails', token=token)
        emails = emails_resp.json()
        primary_email = next((e['email'] for e in emails if e['primary'] and e['verified']), None)
        if primary_email:
            profile['email'] = primary_email

    auth_service = AuthService(db)
    user = auth_service.handle_github_login(profile=profile, access_token=access_token)

    # Generate JWT
    jwt_token = create_access_token(subject=str(user.id))

    # Redirect to frontend with token
    base_url = str(request.base_url).rstrip('/')
    redirect_url = f"{base_url}/?token={jwt_token}"
    return RedirectResponse(url=redirect_url)

@router.get("/me", response_model=UserResponse)
def get_me(current_user = Depends(get_current_user)):
    """
    Returns the profile of the currently authenticated user.
    """
    provider = None
    if current_user.oauth_accounts:
        provider = current_user.oauth_accounts[0].provider
        
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        username=current_user.username,
        provider=provider,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )
