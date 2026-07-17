"""add password_hash to user

Revision ID: a56d0c8ae193
Revises: 4b371ca588bf
Create Date: 2026-07-14 02:30:36.899620

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a56d0c8ae193'
down_revision: Union[str, Sequence[str], None] = '4b371ca588bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()
    if 'users' in tables:
        columns = [c["name"] for c in insp.get_columns("users")]
        if "password_hash" not in columns:
            op.add_column('users', sa.Column('password_hash', sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()
    if 'users' in tables:
        columns = [c["name"] for c in insp.get_columns("users")]
        if "password_hash" in columns:
            op.drop_column('users', 'password_hash')
