from typing import Any
from authlib.integrations.starlette_client import OAuth
from app.core.config import settings
from app.utils.oauth.base import BaseOAuthProvider, NormalizedProfile

oauth = OAuth()

# Register GitHub client dynamically using Pydantic Settings
oauth.register(
    name="github",
    client_id=settings.GITHUB_CLIENT_ID or "dummy-github-id",
    client_secret=settings.GITHUB_CLIENT_SECRET or "dummy-github-secret",
    access_token_url="https://github.com/login/oauth/access_token",
    access_token_params=None,
    authorize_url="https://github.com/login/oauth/authorize",
    authorize_params=None,
    api_base_url="https://api.github.com/",
    client_kwargs={
        "scope": "user:email read:user",
    }
)


class GitHubOAuthProvider(BaseOAuthProvider):
    """GitHub OAuth provider concrete strategy."""

    async def get_redirect(self, request: Any) -> Any:
        redirect_uri = settings.GITHUB_REDIRECT_URI or "http://127.0.0.1:8000/auth/callback/github"
        return await oauth.github.authorize_redirect(request, redirect_uri)

    async def exchange_code_for_profile(self, code: str, request: Any) -> NormalizedProfile:
        token = await oauth.github.authorize_access_token(request)
        
        # 1. Fetch main profile
        resp = await oauth.github.get("user", token=token)
        profile = resp.json()

        # 2. Fetch email addresses (handles private emails)
        email = profile.get("email")
        if not email:
            email_resp = await oauth.github.get("user/emails", token=token)
            emails = email_resp.json()
            if isinstance(emails, list):
                for email_info in emails:
                    if email_info.get("primary") and email_info.get("verified"):
                        email = email_info.get("email")
                        break
                if not email and emails:
                    email = emails[0].get("email")

        from datetime import datetime, timezone
        expires_at_int = token.get("expires_at")
        expires_at = None
        if expires_at_int:
            expires_at = datetime.fromtimestamp(expires_at_int, tz=timezone.utc).replace(tzinfo=None)

        return {
            "provider": "github",
            "provider_user_id": str(profile.get("id")),
            "email": email or "",
            "full_name": profile.get("name") or profile.get("login") or "",
            "avatar_url": profile.get("avatar_url"),
            "access_token": token.get("access_token"),
            "refresh_token": token.get("refresh_token"),
            "expires_at": expires_at,
        }
