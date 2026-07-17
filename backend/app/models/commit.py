import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import CommitStatus

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.webhook_event import WebhookEvent


class Commit(BaseModel):
    """
    Stores structured, normalized commit metadata extracted from GitHub push event payloads.

    Each Commit record is produced during webhook ingestion and begins with
    status = PENDING so that Milestone 6 background workers can pick it up for
    downstream processing (AI summarisation, embeddings, documentation generation)
    without requiring a schema migration.

    Foreign Keys:
        repository_id    → repositories.id   (CASCADE delete)
        webhook_event_id → webhook_events.id  (CASCADE delete)

    Future Milestones Using This Table:
        - Activity Feed      : committed_at, author_name, commit_message, repository_id
        - Developer Dashboard: author_email, author_username, committed_at
        - AI Documentation   : raw_payload, commit_message, added/modified/removed_files
        - Search             : commit_message, author_name, github_commit_sha
        - Analytics          : committed_at, repository_id, author_email, file change arrays
        - Background Workers : WHERE status = 'PENDING' LIMIT N
    """

    __tablename__ = "commits"

    __table_args__ = (
        # Prevent the same commit SHA being ingested twice for the same repository.
        # Uses repository-scoped uniqueness (not global) to handle fork scenarios.
        UniqueConstraint(
            "github_commit_sha",
            "repository_id",
            name="uq_commits_sha_repository_id",
        ),
        # Composite index for the most common query: commits by repo ordered by time
        Index(
            "ix_commits_repository_id_committed_at",
            "repository_id",
            "committed_at",
        ),
    )

    # ── Foreign Keys ────────────────────────────────────────────────────────────

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The connected repository this commit belongs to.",
    )

    webhook_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("webhook_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="The raw webhook delivery that produced this commit record.",
    )

    # ── Git Commit Identity ──────────────────────────────────────────────────────

    github_commit_sha: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        comment="Full 40-character git commit SHA — canonical identifier.",
    )

    short_sha: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        comment="First 8 characters of the SHA — for display purposes.",
    )

    # ── Commit Content ───────────────────────────────────────────────────────────

    commit_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full commit message body as provided by GitHub.",
    )

    commit_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="GitHub HTML URL to the commit (e.g. https://github.com/owner/repo/commit/sha).",
    )

    # ── Temporal ─────────────────────────────────────────────────────────────────

    committed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Authoritative commit timestamp from the GitHub payload (timezone-aware).",
    )

    # ── Branch ───────────────────────────────────────────────────────────────────

    branch: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Branch the push targeted, parsed from payload ref (e.g. 'main').",
    )

    # ── Author Metadata ───────────────────────────────────────────────────────────

    author_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Git author name field from the commit.",
    )

    author_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Git author email — used for Developer Dashboard attribution queries.",
    )

    author_username: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="GitHub username of the author — absent for non-GitHub users.",
    )

    # ── File Change Metadata ──────────────────────────────────────────────────────

    added_files: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
        comment="List of file paths added in this commit.",
    )

    modified_files: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
        comment="List of file paths modified in this commit.",
    )

    removed_files: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
        comment="List of file paths removed in this commit.",
    )

    # ── Raw Payload ────────────────────────────────────────────────────────────────

    raw_payload: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Full raw commit object from the GitHub push payload — used by AI processing in Milestone 6.",
    )

    # ── Processing State ──────────────────────────────────────────────────────────

    status: Mapped[CommitStatus] = mapped_column(
        Enum(CommitStatus),
        nullable=False,
        default=CommitStatus.PENDING,
        server_default=CommitStatus.PENDING.value,
        index=True,
        comment="Processing lifecycle state. PENDING until a background worker picks this up.",
    )

    # ── Relationships ──────────────────────────────────────────────────────────────

    repository: Mapped["Repository"] = relationship(
        back_populates="commits",
    )

    webhook_event: Mapped["WebhookEvent"] = relationship(
        back_populates="commits",
    )
