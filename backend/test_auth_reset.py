import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.main import app
from app.db.session import get_db, engine
from app.models.base import BaseModel as Base
from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.core.security import verify_password
import datetime
from datetime import timezone

# Setup test DB (Assuming standard setup for existing tests)
client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    # Similar to existing tests, we assume get_db yields a session
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    yield db
    # We don't drop all tables because other tests might run in parallel or sequence

def test_forgot_password_success(db_session: Session):
    # Register a user
    email = "forgot_test@example.com"
    
    # Ensure user is deleted
    existing = db_session.scalars(select(User).where(User.email == email)).first()
    if existing:
        db_session.delete(existing)
        db_session.commit()

    client.post("/auth/register", json={
        "full_name": "Forgot Test",
        "email": email,
        "password": "old_password123"
    })

    # Request reset
    response = client.post("/auth/forgot-password", json={"email": email})
    assert response.status_code == 200
    assert "If an account with that email exists" in response.json()["message"]

    # Verify token exists
    user = db_session.scalars(select(User).where(User.email == email)).first()
    token = db_session.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)).first()
    
    assert token is not None
    assert token.used_at is None
    assert token.expires_at > datetime.datetime.now(timezone.utc)


def test_forgot_password_unknown_email(db_session: Session):
    response = client.post("/auth/forgot-password", json={"email": "unknown_doesnotexist@example.com"})
    assert response.status_code == 200
    assert "If an account with that email exists" in response.json()["message"]


def test_reset_password_success(db_session: Session):
    email = "reset_test@example.com"
    
    # Ensure user is deleted
    existing = db_session.scalars(select(User).where(User.email == email)).first()
    if existing:
        db_session.delete(existing)
        db_session.commit()

    client.post("/auth/register", json={
        "full_name": "Reset Test",
        "email": email,
        "password": "old_password123"
    })

    # We need a token, so let's trigger forgot password
    client.post("/auth/forgot-password", json={"email": email})

    # Manually retrieve token hash from db and pretend we got the raw token
    # Since we can't get the raw token (it was hashed), we'll inject a known one for testing
    import secrets, hashlib
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    user = db_session.scalars(select(User).where(User.email == email)).first()
    token = db_session.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)).first()
    token.token_hash = token_hash
    db_session.commit()

    # Reset Password
    response = client.post("/auth/reset-password", json={
        "token": raw_token,
        "new_password": "new_password456"
    })
    
    assert response.status_code == 200
    assert response.json()["message"] == "Password successfully updated."

    # Verify password was updated
    db_session.refresh(user)
    assert verify_password("new_password456", user.password_hash)

    # Verify token is used
    db_session.refresh(token)
    assert token.used_at is not None

def test_reset_password_used_token(db_session: Session):
    email = "reset_test@example.com"
    
    import secrets, hashlib
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    
    user = db_session.scalars(select(User).where(User.email == email)).first()
    token = db_session.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)).first()
    token.token_hash = token_hash
    db_session.commit()

    # Try resetting again (token is already used from previous test logic if we reuse)
    # Actually wait, let's just make it used
    token.used_at = datetime.datetime.now(timezone.utc)
    db_session.commit()

    response = client.post("/auth/reset-password", json={
        "token": raw_token,
        "new_password": "another_password789"
    })
    
    assert response.status_code == 400
    assert "already been used" in response.json()["detail"]

def test_reset_password_invalid_token(db_session: Session):
    response = client.post("/auth/reset-password", json={
        "token": "invalid_raw_token_xyz",
        "new_password": "somepassword123"
    })
    
    assert response.status_code == 400
    assert "Invalid or expired" in response.json()["detail"]
