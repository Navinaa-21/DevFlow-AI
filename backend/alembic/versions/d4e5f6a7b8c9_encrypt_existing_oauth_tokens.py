"""encrypt existing oauth tokens

Revision ID: d4e5f6a7b8c9
Revises: 1cdd5e7433e2
Create Date: 2026-08-10 16:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet, InvalidToken

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = '1cdd5e7433e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Data Migration: Safely encrypts existing plaintext OAuth tokens in the database.
    
    Safety features:
    - Reads OAUTH_TOKEN_ENCRYPTION_KEY from environment or configuration.
    - Uses Fernet decryption attempt to check if a token is already encrypted (prevents double-encryption).
    - Fails early with a clear exception if key is missing/invalid.
    """
    bind = op.get_bind()
    session = Session(bind=bind)

    import os
    encryption_key = os.getenv("OAUTH_TOKEN_ENCRYPTION_KEY")
    if not encryption_key:
        # Fallback to app config if available
        try:
            from app.core.config import settings
            encryption_key = settings.OAUTH_TOKEN_ENCRYPTION_KEY
        except Exception:
            pass

    if not encryption_key:
        raise ValueError(
            "CRITICAL: Cannot run migration 'd4e5f6a7b8c9'. "
            "Environment variable 'OAUTH_TOKEN_ENCRYPTION_KEY' is missing or empty."
        )

    try:
        fernet = Fernet(encryption_key.encode("utf-8") if isinstance(encryption_key, str) else encryption_key)
    except Exception as e:
        raise ValueError(f"CRITICAL: Invalid OAUTH_TOKEN_ENCRYPTION_KEY format: {str(e)}")

    # Fetch all oauth_accounts rows using raw SQL to remain independent of ORM changes
    result = bind.execute(sa.text("SELECT id, access_token, refresh_token FROM oauth_accounts"))
    rows = result.fetchall()

    for row in rows:
        account_id = row[0]
        access_token = row[1]
        refresh_token = row[2]

        updated_fields = {}

        # Safely handle access_token
        if access_token:
            is_encrypted = False
            try:
                fernet.decrypt(access_token.encode("utf-8"))
                is_encrypted = True
            except InvalidToken:
                is_encrypted = False
            except Exception:
                is_encrypted = False

            if not is_encrypted:
                encrypted_val = fernet.encrypt(access_token.encode("utf-8")).decode("utf-8")
                updated_fields["access_token"] = encrypted_val

        # Safely handle refresh_token
        if refresh_token:
            is_encrypted = False
            try:
                fernet.decrypt(refresh_token.encode("utf-8"))
                is_encrypted = True
            except InvalidToken:
                is_encrypted = False
            except Exception:
                is_encrypted = False

            if not is_encrypted:
                encrypted_val = fernet.encrypt(refresh_token.encode("utf-8")).decode("utf-8")
                updated_fields["refresh_token"] = encrypted_val

        if updated_fields:
            stmt = sa.text(
                "UPDATE oauth_accounts SET " + 
                ", ".join(f"{k} = :{k}" for k in updated_fields.keys()) + 
                " WHERE id = :id"
            )
            updated_fields["id"] = account_id
            bind.execute(stmt, updated_fields)


def downgrade() -> None:
    """
    Downgrade Guard: Encrypted production OAuth tokens must NOT be converted back to plaintext.
    """
    raise RuntimeError(
        "Downgrade prohibited for security migration 'd4e5f6a7b8c9': "
        "Encrypted production OAuth tokens must not be downgraded to plaintext."
    )
