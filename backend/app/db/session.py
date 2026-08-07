from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Create synchronous engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# Synchronous session factory representing SessionLocal
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency injection provider for synchronous Session.
    Yields a Session instance and closes it after the request completes.
    """
    db = SessionLocal()
    try:
        yield db #generator function
    finally:
        db.close()
