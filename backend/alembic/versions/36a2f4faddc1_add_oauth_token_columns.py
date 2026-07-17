"""add_oauth_token_columns

Revision ID: 36a2f4faddc1
Revises: afb680315ef7
Create Date: 2026-07-13 12:32:53.332858

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36a2f4faddc1'
down_revision: Union[str, Sequence[str], None] = 'afb680315ef7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()
    if 'oauth_accounts' in tables:
        columns = [c["name"] for c in insp.get_columns("oauth_accounts")]
        if "access_token" not in columns:
            op.add_column('oauth_accounts', sa.Column('access_token', sa.String(length=1000), nullable=True))
        if "refresh_token" not in columns:
            op.add_column('oauth_accounts', sa.Column('refresh_token', sa.String(length=1000), nullable=True))
        if "expires_at" not in columns:
            op.add_column('oauth_accounts', sa.Column('expires_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()
    if 'oauth_accounts' in tables:
        columns = [c["name"] for c in insp.get_columns("oauth_accounts")]
        if "expires_at" in columns:
            op.drop_column('oauth_accounts', 'expires_at')
        if "refresh_token" in columns:
            op.drop_column('oauth_accounts', 'refresh_token')
        if "access_token" in columns:
            op.drop_column('oauth_accounts', 'access_token')
