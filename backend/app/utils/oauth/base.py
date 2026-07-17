from datetime import datetime
from abc import ABC, abstractmethod
from typing import TypedDict, Optional, Any


class NormalizedProfile(TypedDict):
    provider: str
    provider_user_id: str
    email: str
    full_name: str
    avatar_url: Optional[str]
    access_token: Optional[str]
    refresh_token: Optional[str]
    expires_at: Optional[datetime]


class BaseOAuthProvider(ABC):
    """Abstract base class for all OAuth strategy providers."""

    @abstractmethod
    async def get_redirect(self, request: Any) -> Any:
        """Generate and return the redirect URL or RedirectResponse for authorization."""
        pass

    @abstractmethod
    async def exchange_code_for_profile(self, code: str, request: Any) -> NormalizedProfile:
        """Exchange authorization code for access tokens, fetch and normalize user profile."""
        pass
