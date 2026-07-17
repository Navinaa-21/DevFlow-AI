import sys
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.auth_service import AuthService, AuthDomainError
from app.repositories.user_repository import UserRepository

def run_tests():
    engine = create_engine(settings.DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"service_{unique_id}@example.com"
    oauth_email = f"oauth_{unique_id}@example.com"
    test_password = "SecurePassword123!"
    
    auth_service = AuthService(db)
    user_repo = UserRepository(db)
    
    try:
        print("Running AuthService tests...")
        
        # 1. Successful registration
        tokens = auth_service.register_user(
            full_name="Service Test User",
            email=test_email,
            password=test_password
        )
        assert 'access_token' in tokens, "Missing access token"
        print("? register_user returns valid JWT payload on success")
        
        # 2. Duplicate email registration
        try:
            auth_service.register_user(
                full_name="Duplicate User",
                email=test_email,
                password=test_password
            )
            assert False, "Should have raised AuthDomainError for duplicate email"
        except AuthDomainError as e:
            assert "already exists" in str(e).lower()
            print("? register_user correctly rejects duplicate emails")
            
        # 3. Successful login
        tokens = auth_service.login_user(test_email, test_password)
        assert 'access_token' in tokens, "Missing access token on login"
        print("? login_user returns valid JWT payload on success")
        
        # 4. Wrong password
        try:
            auth_service.login_user(test_email, "WrongPassword")
            assert False, "Should have raised AuthDomainError for wrong password"
        except AuthDomainError as e:
            assert "invalid credentials" in str(e).lower()
            print("? login_user correctly rejects incorrect passwords")
            
        # 5. Nonexistent email
        try:
            auth_service.login_user("nobody@nowhere.com", "Password")
            assert False, "Should have raised AuthDomainError for nonexistent email"
        except AuthDomainError as e:
            assert "invalid credentials" in str(e).lower()
            print("? login_user correctly rejects nonexistent emails safely")
            
        # 6. OAuth-only account login attempt
        # Manually create an oauth-only user
        oauth_user = user_repo.create_user("OAuth User", oauth_email, None)
        try:
            auth_service.login_user(oauth_email, "AnyPassword")
            assert False, "Should have rejected OAuth-only account login"
        except AuthDomainError as e:
            assert "third-party provider" in str(e).lower()
            print("? login_user correctly rejects OAuth-only users without a password")
            
        # 7. Inactive account
        # Manually deactivate the main test user
        user = user_repo.get_by_email(test_email)
        user.is_active = False
        db.commit()
        try:
            auth_service.login_user(test_email, test_password)
            assert False, "Should have rejected inactive account login"
        except AuthDomainError as e:
            assert "disabled" in str(e).lower()
            print("? login_user correctly rejects disabled/inactive accounts")
            
        print("\nAll service tests passed successfully!")
        
    except AssertionError as e:
        print(f"? Test Failed: {e}")
        db.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"? Unexpected Error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()

if __name__ == '__main__':
    run_tests()
