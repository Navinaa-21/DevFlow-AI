"""Initial database schema

Revision ID: c7fd402f091e
Revises: 
Create Date: 2026-07-10 15:12:06.622983

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7fd402f091e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()

    if 'users' not in tables:
        op.create_table('users',
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        
    if 'workspaces' not in tables:
        op.create_table('workspaces',
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_workspaces_slug'), 'workspaces', ['slug'], unique=True)
        
    if 'invitations' not in tables:
        op.create_table('invitations',
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('OWNER', 'ADMIN', 'MANAGER', 'DEVELOPER', name='workspacerole'), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'ACCEPTED', 'EXPIRED', 'CANCELLED', name='invitationstatus'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
        )
        op.create_index(op.f('ix_invitations_email'), 'invitations', ['email'], unique=False)
        
    if 'oauth_accounts' not in tables:
        op.create_table('oauth_accounts',
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.Enum('LOCAL', 'GITHUB', 'GOOGLE', 'AZURE', name='authprovider'), nullable=False),
        sa.Column('provider_user_id', sa.String(length=255), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_user_id', name='uq_provider_user_id')
        )
        
    if 'repositories' not in tables:
        op.create_table('repositories',
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.Enum('GITHUB', 'GITLAB', 'AZURE_DEVOPS', name='repositoryprovider'), nullable=False),
        sa.Column('provider_repo_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('repo_url', sa.String(length=500), nullable=False),
        sa.Column('default_branch', sa.String(length=100), nullable=False),
        sa.Column('webhook_enabled', sa.Boolean(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_repositories_provider_repo_id'), 'repositories', ['provider_repo_id'], unique=False)
        
    if 'workspace_members' not in tables:
        op.create_table('workspace_members',
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.Enum('OWNER', 'ADMIN', 'MANAGER', 'DEVELOPER', name='workspacerole'), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_user')
        )
        
    if 'webhook_events' not in tables:
        op.create_table('webhook_events',
        sa.Column('repository_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('delivery_id', sa.String(length=255), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_webhook_events_delivery_id'), 'webhook_events', ['delivery_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()

    # Drop index/tables in reverse dependency order
    if 'webhook_events' in tables:
        op.drop_index(op.f('ix_webhook_events_delivery_id'), table_name='webhook_events')
        op.drop_table('webhook_events')
    if 'workspace_members' in tables:
        op.drop_table('workspace_members')
    if 'repositories' in tables:
        op.drop_index(op.f('ix_repositories_provider_repo_id'), table_name='repositories')
        op.drop_table('repositories')
    if 'oauth_accounts' in tables:
        op.drop_table('oauth_accounts')
    if 'invitations' in tables:
        op.drop_index(op.f('ix_invitations_email'), table_name='invitations')
        op.drop_table('invitations')
    if 'workspaces' in tables:
        op.drop_index(op.f('ix_workspaces_slug'), table_name='workspaces')
        op.drop_table('workspaces')
    if 'users' in tables:
        op.drop_index(op.f('ix_users_email'), table_name='users')
        op.drop_table('users')

    # Drop custom enum types to prevent duplicate type creation errors on re-upgrade
    op.execute("DROP TYPE IF EXISTS workspacerole")
    op.execute("DROP TYPE IF EXISTS invitationstatus")
    op.execute("DROP TYPE IF EXISTS authprovider")
    op.execute("DROP TYPE IF EXISTS repositoryprovider")
