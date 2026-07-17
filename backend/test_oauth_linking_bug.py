import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.db.session import SessionLocal
from app.models.user import User
from app.models.oauth_account import OAuthAccount
from app.models.enums import AuthProvider
from app.services.auth_service import AuthService
from app.utils.oauth.registry import OAuthProviderRegistry
from app.utils.oauth.base import BaseOAuthProvider

async def main():
    db = SessionLocal()
    try:
        # 1. Clean database state for abc@gmail.com
        print("Cleaning up database state...")
        existing_users = db.query(User).filter(User.email == "abc@gmail.com").all()
        for u in existing_users:
            db.delete(u)
        db.commit()

        # 2. Mock provider strategy for Google
        google_mock_provider = MagicMock(spec=BaseOAuthProvider)
        google_mock_provider.exchange_code_for_profile = AsyncMock(return_value={
            "provider": "google",
            "provider_user_id": "google-user-id-123",
            "email": "abc@gmail.com",
            "full_name": "Google User",
            "avatar_url": None,
            "access_token": "g-access",
            "refresh_token": "g-refresh",
            "expires_at": None
        })

        # 3. Mock provider strategy for GitHub
        github_mock_provider = MagicMock(spec=BaseOAuthProvider)
        github_mock_provider.exchange_code_for_profile = AsyncMock(return_value={
            "provider": "github",
            "provider_user_id": "github-user-id-456",
            "email": "abc@gmail.com",
            "full_name": "GitHub User",
            "avatar_url": None,
            "access_token": "gh-access",
            "refresh_token": "gh-refresh",
            "expires_at": None
        })

        # Registry mock map
        registry_map = {
            "google": google_mock_provider,
            "github": github_mock_provider
        }
        
        # Override Registry
        original_registry_get = OAuthProviderRegistry.get
        OAuthProviderRegistry.get = lambda name: registry_map[name.lower()]

        auth_service = AuthService(db)
        mock_request = MagicMock()

        # 4. User logs in with Google first
        print("\n--- Simulating Google OAuth Login ---")
        user_g = await auth_service.authenticate_oauth_callback("google", "code_google", mock_request)
        print(f"Google Login Output -> User: ID={user_g.id}, Email={user_g.email}, Name={user_g.full_name}")

        # Check google accounts count
        google_accounts = db.query(OAuthAccount).filter(OAuthAccount.user_id == user_g.id).all()
        print(f"Google accounts found linked to user ID: {len(google_accounts)}")

        # 5. User logs in with GitHub using the same email
        print("\n--- Simulating GitHub OAuth Login ---")
        user_gh = await auth_service.authenticate_oauth_callback("github", "code_github", mock_request)
        print(f"GitHub Login Output -> User: ID={user_gh.id}, Email={user_gh.email}, Name={user_gh.full_name}")

        # Check github accounts count
        github_accounts = db.query(OAuthAccount).filter(OAuthAccount.user_id == user_gh.id).all()
        print(f"GitHub accounts found linked to user ID: {len(github_accounts)}")

        # Verify only one user row exists
        all_users = db.query(User).filter(User.email == "abc@gmail.com").all()
        print(f"\nVerification Results:")
        print(f"Total User records for email abc@gmail.com: {len(all_users)}")
        
        # Check OAuth Accounts count linked
        all_oauth = db.query(OAuthAccount).filter(OAuthAccount.user_id == user_g.id).all()
        print(f"Total OAuth Accounts referencing user ID {user_g.id}: {len(all_oauth)}")
        for idx, acct in enumerate(all_oauth):
            print(f"  {idx + 1}. Provider: {acct.provider}, Provider User ID: {acct.provider_user_id}")

        assert len(all_users) == 1, f"Assertion Failed: Expected exactly 1 User record, but found {len(all_users)}"
        assert user_g.id == user_gh.id, "Assertion Failed: User IDs do not match!"
        print("\nSUCCESS: OAuth account linking works perfectly in simulation!")

    except Exception as e:
        print(f"\nERROR / ASSERTION FAILURE: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.rollback()
        # Clean up
        users = db.query(User).filter(User.email == "abc@gmail.com").all()
        for u in users:
            db.delete(u)
        db.commit()
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
