"""add_commits_table_enrich_webhook_events

Revision ID: 4b371ca588bf
Revises: 36a2f4faddc1
Create Date: 2026-07-14 00:57:51.250874

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4b371ca588bf'
down_revision: Union[str, Sequence[str], None] = '36a2f4faddc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Use postgresql.ENUM with create_type=False so SQLAlchemy never auto-emits
# CREATE TYPE statements. We manage type creation manually with raw DDL below.
commitstatus = postgresql.ENUM(
    'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED',
    name='commitstatus',
    create_type=False,
)
webhookprocessingstatus = postgresql.ENUM(
    'RECEIVED', 'PROCESSED', 'IGNORED', 'FAILED',
    name='webhookprocessingstatus',
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    from sqlalchemy import inspect
    insp = inspect(conn)
    tables = insp.get_table_names()

    # Step 1 — Create PostgreSQL enum types using a DO block with EXCEPTION guard.
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE commitstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$
    """))
    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE webhookprocessingstatus AS ENUM ('RECEIVED', 'PROCESSED', 'IGNORED', 'FAILED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$
    """))

    # Step 2 — Create the commits table if it doesn't exist
    if 'commits' not in tables:
        op.create_table('commits',
        sa.Column('repository_id', sa.UUID(), nullable=False, comment='The connected repository this commit belongs to.'),
        sa.Column('webhook_event_id', sa.UUID(), nullable=False, comment='The raw webhook delivery that produced this commit record.'),
        sa.Column('github_commit_sha', sa.String(length=40), nullable=False, comment='Full 40-character git commit SHA — canonical identifier.'),
        sa.Column('short_sha', sa.String(length=8), nullable=False, comment='First 8 characters of the SHA — for display purposes.'),
        sa.Column('commit_message', sa.Text(), nullable=False, comment='Full commit message body as provided by GitHub.'),
        sa.Column('commit_url', sa.String(length=500), nullable=False, comment='GitHub HTML URL to the commit (e.g. https://github.com/owner/repo/commit/sha).'),
        sa.Column('committed_at', sa.DateTime(timezone=True), nullable=False, comment='Authoritative commit timestamp from the GitHub payload (timezone-aware).'),
        sa.Column('branch', sa.String(length=255), nullable=False, comment="Branch the push targeted, parsed from payload ref (e.g. 'main')."),
        sa.Column('author_name', sa.String(length=255), nullable=False, comment='Git author name field from the commit.'),
        sa.Column('author_email', sa.String(length=255), nullable=False, comment='Git author email — used for Developer Dashboard attribution queries.'),
        sa.Column('author_username', sa.String(length=255), nullable=True, comment='GitHub username of the author — absent for non-GitHub users.'),
        sa.Column('added_files', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False, comment='List of file paths added in this commit.'),
        sa.Column('modified_files', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False, comment='List of file paths modified in this commit.'),
        sa.Column('removed_files', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False, comment='List of file paths removed in this commit.'),
        sa.Column('raw_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='Full raw commit object from the GitHub push payload — used by AI processing in Milestone 6.'),
        sa.Column('status', commitstatus, server_default='PENDING', nullable=False, comment='Processing lifecycle state. PENDING until a background worker picks this up.'),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], name=op.f('fk_commits_repository_id_repositories'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['webhook_event_id'], ['webhook_events.id'], name=op.f('fk_commits_webhook_event_id_webhook_events'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_commits')),
        sa.UniqueConstraint('github_commit_sha', 'repository_id', name='uq_commits_sha_repository_id')
        )
        op.create_index(op.f('ix_commits_author_email'), 'commits', ['author_email'], unique=False)
        op.create_index(op.f('ix_commits_committed_at'), 'commits', ['committed_at'], unique=False)
        op.create_index(op.f('ix_commits_repository_id'), 'commits', ['repository_id'], unique=False)
        op.create_index('ix_commits_repository_id_committed_at', 'commits', ['repository_id', 'committed_at'], unique=False)
        op.create_index(op.f('ix_commits_status'), 'commits', ['status'], unique=False)
        op.create_index(op.f('ix_commits_webhook_event_id'), 'commits', ['webhook_event_id'], unique=False)

    # Step 3 — Add columns to webhook_events conditionally
    if 'webhook_events' in tables:
        wh_columns = [c["name"] for c in insp.get_columns("webhook_events")]
        if 'processing_status' not in wh_columns:
            op.add_column('webhook_events', sa.Column('processing_status', webhookprocessingstatus, server_default='RECEIVED', nullable=False))
        if 'processed_at' not in wh_columns:
            op.add_column('webhook_events', sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True))
        if 'error_message' not in wh_columns:
            op.add_column('webhook_events', sa.Column('error_message', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    from sqlalchemy import inspect
    bind = op.get_bind()
    insp = inspect(bind)
    tables = insp.get_table_names()

    if 'webhook_events' in tables:
        wh_columns = [c["name"] for c in insp.get_columns("webhook_events")]
        if 'error_message' in wh_columns:
            op.drop_column('webhook_events', 'error_message')
        if 'processed_at' in wh_columns:
            op.drop_column('webhook_events', 'processed_at')
        if 'processing_status' in wh_columns:
            op.drop_column('webhook_events', 'processing_status')

    if 'commits' in tables:
        comm_indexes = [idx["name"] for idx in insp.get_indexes("commits")]
        if 'ix_commits_webhook_event_id' in comm_indexes:
            op.drop_index(op.f('ix_commits_webhook_event_id'), table_name='commits')
        if 'ix_commits_status' in comm_indexes:
            op.drop_index(op.f('ix_commits_status'), table_name='commits')
        if 'ix_commits_repository_id_committed_at' in comm_indexes:
            op.drop_index('ix_commits_repository_id_committed_at', table_name='commits')
        if 'ix_commits_repository_id' in comm_indexes:
            op.drop_index(op.f('ix_commits_repository_id'), table_name='commits')
        if 'ix_commits_committed_at' in comm_indexes:
            op.drop_index(op.f('ix_commits_committed_at'), table_name='commits')
        if 'ix_commits_author_email' in comm_indexes:
            op.drop_index(op.f('ix_commits_author_email'), table_name='commits')
        op.drop_table('commits')

    bind.execute(sa.text("DROP TYPE IF EXISTS commitstatus"))
    bind.execute(sa.text("DROP TYPE IF EXISTS webhookprocessingstatus"))
