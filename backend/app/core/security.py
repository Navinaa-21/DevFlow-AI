import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from joserfc import jwt
from joserfc.jwk import OctKey
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def _create_token(subject: str, expires_delta: timedelta) -> str:
    now = int(datetime.utcnow().timestamp())
    expire = now + int(expires_delta.total_seconds())
    
    claims = {
        "sub": subject,
        "exp": expire,
        "iat": now
    }
    
    # Create the key for HS256
    key = OctKey.import_key(settings.JWT_SECRET_KEY)
    header = {"alg": settings.JWT_ALGORITHM}
    
    return jwt.encode(header, claims, key)

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire_time = expires_delta
    else:
        expire_time = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _create_token(subject, expire_time)

def create_refresh_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire_time = expires_delta
    else:
        expire_time = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _create_token(subject, expire_time)

def decode_token(token: str) -> dict:
    key = OctKey.import_key(settings.JWT_SECRET_KEY)
    try:
        claims = jwt.decode(token, key)
        return claims.claims
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Decodes the JWT token and returns the current user object via AuthRepository.
    """
    from app.repositories.auth_repository import AuthRepository
    
    claims = decode_token(token)
    user_id_str = claims.get("sub")
    
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID format in token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_repo = AuthRepository(db)
    user = auth_repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user
