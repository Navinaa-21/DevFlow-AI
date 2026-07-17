"""add_repository_metadata_columns

Revision ID: f1a2b3c4d5e6
Revises: afb680315ef7
Create Date: 2026-07-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'a56d0c8ae193'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()
    
    if 'repositories' in tables:
        columns = [c["name"] for c in insp.get_columns("repositories")]
        if "clone_url" not in columns:
            op.add_column('repositories', sa.Column('clone_url', sa.String(length=500), nullable=True))
        if "visibility" not in columns:
            op.add_column('repositories', sa.Column('visibility', sa.String(length=50), nullable=False, server_default='private'))
        if "last_synced_at" not in columns:
            op.add_column('repositories', sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True))

        op.alter_column('repositories', 'full_name', existing_type=sa.String(length=255), nullable=True)
        op.alter_column('repositories', 'repo_url', existing_type=sa.String(length=500), nullable=True)


def downgrade() -> None:
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()
    
    if 'repositories' in tables:
        columns = [c["name"] for c in insp.get_columns("repositories")]
        if "last_synced_at" in columns:
            op.drop_column('repositories', 'last_synced_at')
        if "visibility" in columns:
            op.drop_column('repositories', 'visibility')
        if "clone_url" in columns:
            op.drop_column('repositories', 'clone_url')
            
        op.alter_column('repositories', 'full_name', existing_type=sa.String(length=255), nullable=False)
        op.alter_column('repositories', 'repo_url', existing_type=sa.String(length=500), nullable=False)
