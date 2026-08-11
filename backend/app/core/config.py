import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings loader using Pydantic settings.
    Loads variables from the environment or a .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    PROJECT_NAME: str = "DevFlow AI"
    APP_NAME: str = "DevFlow AI"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/devflow_ai"

    # Authentication & JWT
    SESSION_SECRET_KEY: str = "change_me_session"
    JWT_SECRET_KEY: str = "change_me_jwt"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    FRONTEND_URL: str = "http://localhost:8000"

    # GitHub OAuth & Encryption
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    OAUTH_TOKEN_ENCRYPTION_KEY: Optional[str] = None

    # GitHub Webhook
    GITHUB_WEBHOOK_SECRET: str = "change_me"

    # AI Service
    OPENAI_API_KEY: Optional[str] = None
    AI_MODEL_NAME: str = "gpt-4"

    # Groq AI Service
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL_NAME: str = "llama-3.1-8b-instant"


# Global settings instance
settings = Settings()
