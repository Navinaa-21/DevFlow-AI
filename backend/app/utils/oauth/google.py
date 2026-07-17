from typing import Any
from authlib.integrations.starlette_client import OAuth
from app.core.config import settings
from app.utils.oauth.base import BaseOAuthProvider, NormalizedProfile

oauth = OAuth()

# Register Google client dynamically using Pydantic Settings
oauth.register(
    name="google",
    client_id=settings.GOOGLE_CLIENT_ID or "dummy-google-id",
    client_secret=settings.GOOGLE_CLIENT_SECRET or "dummy-google-secret",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile",
    }
)


class GoogleOAuthProvider(BaseOAuthProvider):
    """Google OAuth provider concrete strategy."""

    async def get_redirect(self, request: Any) -> Any:
        redirect_uri = settings.GOOGLE_REDIRECT_URI or "http://127.0.0.1:8000/auth/callback/google"
        return await oauth.google.authorize_redirect(request, redirect_uri)

    async def exchange_code_for_profile(self, code: str, request: Any) -> NormalizedProfile:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token.get("userinfo")
        if not userinfo:
            resp = await oauth.google.get("https://www.googleapis.com/oauth2/v3/userinfo", token=token)
            userinfo = resp.json()

        from datetime import datetime, timezone
        expires_at_int = token.get("expires_at")
        expires_at = None
        if expires_at_int:
            expires_at = datetime.fromtimestamp(expires_at_int, tz=timezone.utc).replace(tzinfo=None)

        return {
            "provider": "google",
            "provider_user_id": str(userinfo.get("sub")),
            "email": userinfo.get("email"),
            "full_name": userinfo.get("name", ""),
            "avatar_url": userinfo.get("picture"),
            "access_token": token.get("access_token"),
            "refresh_token": token.get("refresh_token"),
            "expires_at": expires_at,
        }
