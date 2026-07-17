import sys
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.repositories.user_repository import UserRepository
from app.models.base import Base

def run_tests():
    engine = create_engine(settings.DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    # We will use a unique email to avoid conflicts with existing data
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"test_{unique_id}@example.com"
    
    repo = UserRepository(db)
    
    try:
        print("Running UserRepository tests...")
        
        # 1. Nonexistent lookup
        assert repo.get_by_email(test_email) is None, "Should return None for nonexistent email"
        assert repo.email_exists(test_email) is False, "Should return False for nonexistent email"
        print("? get_by_email and email_exists safely handle nonexistent lookups")
        
        # 2. create_user
        user = repo.create_user(
            full_name="Test User",
            email=test_email,
            password_hash="some_hashed_password_123"
        )
        assert user.id is not None, "User should have an ID after commit"
        assert user.email == test_email, "Email should match"
        print("? create_user successfully inserts and refreshes the ORM object")
        
        # 3. get_by_email
        fetched_user = repo.get_by_email(test_email)
        assert fetched_user is not None, "Should find the user we just created"
        assert fetched_user.id == user.id, "IDs should match"
        print("? get_by_email successfully finds existing users")
        
        # 4. email_exists
        assert repo.email_exists(test_email) is True, "Should return True for existing email"
        print("? email_exists successfully identifies duplicate/existing lookups")
        
        # Cleanup
        repo.delete(user.id)
        
        print("\nAll repository tests passed successfully!")
        
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
