import os
import hashlib
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from joserfc import jwt
from joserfc.jwk import OctKey

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

# Define the OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="auth/login",
    auto_error=False
)


def _get_signing_key() -> OctKey:
    """Helper to convert the JWT Secret Key string into a joserfc OctKey."""
    return OctKey.import_key(settings.JWT_SECRET_KEY.encode("utf-8"))


# --- Password Hashing Utilities ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Generate a secure bcrypt hash of a password."""
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plain password against a bcrypt hash. Safely handles malformed hashes."""
    try:
        return pwd_context.verify(password, password_hash)
    except Exception:
        return False


# --- JWT Token Utilities ---
def create_token(
    subject: Union[str, Any],
    expires_delta: timedelta,
    token_type: str
) -> str:
    """Generate a signed JSON Web Token."""
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    
    header = {"alg": settings.JWT_ALGORITHM}
    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": token_type
    }
    
    key = _get_signing_key()
    return jwt.encode(header, payload, key)


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generate a signed Access Token."""
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_token(subject, delta, "access")


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Generate a signed Refresh Token."""
    delta = expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return create_token(subject, delta, "refresh")


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a signed JWT token, raising ValueError on failure or expiration."""
    try:
        key = _get_signing_key()
        result = jwt.decode(token, key)
        claims = result.claims
        
        # Check token expiration
        exp = claims.get("exp")
        if not exp or datetime.now(timezone.utc).timestamp() > exp:
            raise ValueError("Token has expired")
            
        return claims
    except Exception as e:
        raise ValueError(f"Invalid token signature: {str(e)}")


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency injecting the currently authenticated User record.
    Raises HTTP 401 on signature verification or identity retrieval failure.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    try:
        claims = decode_token(token)
        if claims.get("type") != "access":
            raise ValueError("Invalid token type")
        user_id_str = claims.get("sub")
        if not user_id_str:
            raise ValueError("Missing subject identity claim")
        user_id = UUID(user_id_str)
    except Exception:
        raise credentials_exception

    # Query the user database to check if user exists and is active
    statement = select(User).where(User.id == user_id)
    user = db.scalars(statement).first()
    if not user or not user.is_active:
        raise credentials_exception

    return user
