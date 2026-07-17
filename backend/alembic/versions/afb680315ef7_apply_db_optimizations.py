"""apply_db_optimizations

Revision ID: afb680315ef7
Revises: c7fd402f091e
Create Date: 2026-07-13 10:14:57.103114

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'afb680315ef7'
down_revision: Union[str, Sequence[str], None] = 'c7fd402f091e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    
    tables = insp.get_table_names()
    if 'invitations' in tables:
        inv_constraints = [c["name"] for c in insp.get_unique_constraints("invitations")]
        inv_indexes = [idx["name"] for idx in insp.get_indexes("invitations")]
        
        if 'invitations_token_key' in inv_constraints or 'invitations_token_key' in inv_indexes:
            try:
                op.drop_constraint('invitations_token_key', 'invitations', type_='unique')
            except Exception:
                pass

        if 'ix_invitations_workspace_id' not in inv_indexes:
            op.create_index(op.f('ix_invitations_workspace_id'), 'invitations', ['workspace_id'], unique=False)
        if 'uq_invitations_token' not in inv_constraints and 'uq_invitations_token' not in inv_indexes:
            op.create_unique_constraint(op.f('uq_invitations_token'), 'invitations', ['token'])
        if 'uq_workspace_invite_email' not in inv_constraints and 'uq_workspace_invite_email' not in inv_indexes:
            op.create_index('uq_workspace_invite_email', 'invitations', ['workspace_id', 'email'], unique=True, postgresql_where=sa.text("status = 'PENDING'"))

    if 'repositories' in tables:
        repo_constraints = [c["name"] for c in insp.get_unique_constraints("repositories")]
        repo_indexes = [idx["name"] for idx in insp.get_indexes("repositories")]
        if 'ix_repositories_workspace_id' not in repo_indexes:
            op.create_index(op.f('ix_repositories_workspace_id'), 'repositories', ['workspace_id'], unique=False)
        if 'uq_workspace_provider_repo' not in repo_constraints:
            op.create_unique_constraint('uq_workspace_provider_repo', 'repositories', ['workspace_id', 'provider', 'provider_repo_id'])

    if 'webhook_events' in tables:
        wh_indexes = [idx["name"] for idx in insp.get_indexes("webhook_events")]
        col_type = next((col["type"] for col in insp.get_columns("webhook_events") if col["name"] == "payload"), None)
        if col_type is not None and not str(col_type).startswith("JSONB"):
            op.alter_column('webhook_events', 'payload',
                       existing_type=postgresql.JSON(astext_type=sa.Text()),
                       type_=postgresql.JSONB(astext_type=sa.Text()),
                       existing_nullable=False)
        if 'ix_webhook_events_repository_id' not in wh_indexes:
            op.create_index(op.f('ix_webhook_events_repository_id'), 'webhook_events', ['repository_id'], unique=False)

    if 'workspace_members' in tables:
        m_indexes = [idx["name"] for idx in insp.get_indexes("workspace_members")]
        if 'ix_workspace_members_user_id' not in m_indexes:
            op.create_index(op.f('ix_workspace_members_user_id'), 'workspace_members', ['user_id'], unique=False)
        if 'ix_workspace_members_workspace_id' not in m_indexes:
            op.create_index(op.f('ix_workspace_members_workspace_id'), 'workspace_members', ['workspace_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()

    if 'workspace_members' in tables:
        m_indexes = [idx["name"] for idx in insp.get_indexes("workspace_members")]
        if 'ix_workspace_members_workspace_id' in m_indexes:
            op.drop_index(op.f('ix_workspace_members_workspace_id'), table_name='workspace_members')
        if 'ix_workspace_members_user_id' in m_indexes:
            op.drop_index(op.f('ix_workspace_members_user_id'), table_name='workspace_members')

    if 'webhook_events' in tables:
        wh_indexes = [idx["name"] for idx in insp.get_indexes("webhook_events")]
        if 'ix_webhook_events_repository_id' in wh_indexes:
            op.drop_index(op.f('ix_webhook_events_repository_id'), table_name='webhook_events')
        
        col_type = next((col["type"] for col in insp.get_columns("webhook_events") if col["name"] == "payload"), None)
        if col_type is not None and str(col_type).startswith("JSONB"):
            op.alter_column('webhook_events', 'payload',
                       existing_type=postgresql.JSONB(astext_type=sa.Text()),
                       type_=postgresql.JSON(astext_type=sa.Text()),
                       existing_nullable=False)

    if 'repositories' in tables:
        repo_constraints = [c["name"] for c in insp.get_unique_constraints("repositories")]
        repo_indexes = [idx["name"] for idx in insp.get_indexes("repositories")]
        if 'uq_workspace_provider_repo' in repo_constraints:
            op.drop_constraint('uq_workspace_provider_repo', 'repositories', type_='unique')
        if 'ix_repositories_workspace_id' in repo_indexes:
            op.drop_index(op.f('ix_repositories_workspace_id'), table_name='repositories')

    if 'invitations' in tables:
        inv_constraints = [c["name"] for c in insp.get_unique_constraints("invitations")]
        inv_indexes = [idx["name"] for idx in insp.get_indexes("invitations")]
        if 'uq_workspace_invite_email' in inv_constraints:
            op.drop_constraint('uq_workspace_invite_email', 'invitations', type_='unique')
        elif 'uq_workspace_invite_email' in inv_indexes:
            op.drop_index('uq_workspace_invite_email', table_name='invitations')
        if 'uq_invitations_token' in inv_constraints:
            op.drop_constraint(op.f('uq_invitations_token'), 'invitations', type_='unique')
        if 'ix_invitations_workspace_id' in inv_indexes:
            op.drop_index(op.f('ix_invitations_workspace_id'), table_name='invitations')
        
        if 'invitations_token_key' not in inv_constraints and 'invitations_token_key' not in inv_indexes:
            op.create_unique_constraint(op.f('invitations_token_key'), 'invitations', ['token'])
