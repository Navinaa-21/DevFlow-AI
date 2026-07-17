from typing import Dict, Type
from app.utils.oauth.base import BaseOAuthProvider
from app.utils.oauth.google import GoogleOAuthProvider
from app.utils.oauth.github import GitHubOAuthProvider


class ProviderNotSupportedError(Exception):
    """Exception raised when an unsupported OAuth provider is requested."""
    pass


class OAuthProviderRegistry:
    """Registry class implementing the Strategy Pattern for OAuth providers."""

    _strategies: Dict[str, Type[BaseOAuthProvider]] = {
        "google": GoogleOAuthProvider,
        "github": GitHubOAuthProvider,
    }

    @classmethod
    def get(cls, provider: str) -> BaseOAuthProvider:
        """Resolve a provider key (e.g. 'google') to its concrete strategy instance."""
        strategy_class = cls._strategies.get(provider.lower())
        if not strategy_class:
            raise ProviderNotSupportedError(f"OAuth Provider '{provider}' is not supported.")
        return strategy_class()
