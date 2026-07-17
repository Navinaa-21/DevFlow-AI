from typing import List, Optional, Sequence
from uuid import UUID

from sqlalchemy import desc, exists, select
from sqlalchemy.orm import Session

from app.models.commit import Commit
from app.models.enums import CommitStatus
from app.repositories.base import BaseRepository


class CommitRepository(BaseRepository[Commit]):
    """
    Repository handling all database access for the Commit model.

    Responsibilities:
        - Bulk-inserting extracted commit records from push event payloads.
        - Querying commits by SHA for deduplication and lookup.
        - Querying commits by repository, author, branch for feeds and dashboards.
        - Querying pending commits for background worker pickup (Milestone 6).

    This class contains ONLY database access logic.
    Business rules, commit extraction, and processing decisions belong in the service layer.
    """

    def __init__(self, db: Session):
        super().__init__(Commit, db)

    # ── Write Operations ────────────────────────────────────────────────────────

    def bulk_create_commits(self, commits: List[Commit]) -> List[Commit]:
        """
        Persist multiple Commit ORM objects in a single batch database operation.

        All commits are inserted via db.add_all() — a single database round-trip
        rather than N individual INSERTs. All commits in the batch are committed
        atomically: if any insert fails, the entire batch rolls back.

        Every commit must already have status=PENDING set by the caller (the service
        layer). This repository does not enforce business rules on the status field.

        Args:
            commits: List of pre-constructed Commit ORM objects. May be empty.

        Returns:
            The same list of Commit objects, each refreshed with their database-
            assigned id, created_at, and updated_at values. Returns an empty list
            if the input is empty.
        """
        if not commits:
            return []

        self.db.add_all(commits)
        self.db.commit()
        for commit in commits:
            self.db.refresh(commit)
        return commits

    # ── Read Operations ─────────────────────────────────────────────────────────

    def get_by_sha(self, repository_id: UUID, sha: str) -> Optional[Commit]:
        """
        Fetch a single Commit by its SHA within a specific repository.

        Uses the uq_commits_sha_repository_id unique constraint index for
        guaranteed O(1) lookup. Returns None if the commit has not been ingested.

        Args:
            repository_id: UUID of the repository to scope the lookup to.
            sha:           Full 40-character git commit SHA.

        Returns:
            The matching Commit ORM object or None.
        """
        statement = select(Commit).where(
            Commit.repository_id == repository_id,
            Commit.github_commit_sha == sha,
        )
        return self.db.scalars(statement).first()

    def commit_exists(self, repository_id: UUID, sha: str) -> bool:
        """
        Check whether a specific commit SHA has already been ingested for a repository.

        Uses an EXISTS subquery — more efficient than fetching the full row when only
        a boolean presence check is needed. Used in the service layer before bulk
        insert to skip duplicate commits without relying on IntegrityError catching.

        Uses the uq_commits_sha_repository_id index for O(1) evaluation.

        Args:
            repository_id: UUID of the repository.
            sha:           Full 40-character git commit SHA.

        Returns:
            True if the commit already exists, False otherwise.
        """
        statement = select(
            exists().where(
                Commit.repository_id == repository_id,
                Commit.github_commit_sha == sha,
            )
        )
        return self.db.scalar(statement) or False

    def get_by_repository(
        self,
        repository_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[Commit]:
        """
        Fetch a paginated list of commits for a specific repository.

        Ordered by committed_at descending (most recent first) — the standard
        ordering for commit history views and activity feeds.

        Uses the ix_commits_repository_id_committed_at composite index for
        efficient sorting without a full table scan.

        Args:
            repository_id: UUID of the repository.
            skip:          Pagination offset.
            limit:         Maximum number of records to return.

        Returns:
            Sequence of Commit ORM objects ordered by committed_at DESC.
        """
        statement = (
            select(Commit)
            .where(Commit.repository_id == repository_id)
            .order_by(desc(Commit.committed_at))
            .offset(skip)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def list_by_author(
        self,
        repository_id: UUID,
        author_email: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[Commit]:
        """
        Fetch commits for a repository filtered by the author's email address.

        Designed for the Developer Dashboard — shows all commits by a specific
        developer within a repository, ordered most recent first.

        Uses ix_commits_repository_id for the repository filter and
        ix_commits_author_email for the email filter.

        Args:
            repository_id: UUID of the repository.
            author_email:  Exact author email to filter by (case-sensitive).
            skip:          Pagination offset.
            limit:         Maximum number of records to return.

        Returns:
            Sequence of Commit ORM objects for this author, newest first.
        """
        statement = (
            select(Commit)
            .where(
                Commit.repository_id == repository_id,
                Commit.author_email == author_email,
            )
            .order_by(desc(Commit.committed_at))
            .offset(skip)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def list_by_branch(
        self,
        repository_id: UUID,
        branch: str,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[Commit]:
        """
        Fetch commits for a repository filtered by branch name.

        Designed for branch-level commit history views. Ordered most recent first.

        Uses ix_commits_repository_id for scoping.

        Args:
            repository_id: UUID of the repository.
            branch:        Exact branch name to filter by (e.g. "main").
            skip:          Pagination offset.
            limit:         Maximum number of records to return.

        Returns:
            Sequence of Commit ORM objects for this branch, newest first.
        """
        statement = (
            select(Commit)
            .where(
                Commit.repository_id == repository_id,
                Commit.branch == branch,
            )
            .order_by(desc(Commit.committed_at))
            .offset(skip)
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def get_latest_commit(self, repository_id: UUID) -> Optional[Commit]:
        """
        Fetch the single most recently committed record for a repository.

        Uses the ix_commits_repository_id_committed_at composite index for
        efficient retrieval — avoids a full repository scan.

        Useful for repository cards and dashboard summary widgets showing
        the last known activity for a connected repository.

        Args:
            repository_id: UUID of the repository.

        Returns:
            The most recent Commit ORM object or None if no commits exist.
        """
        statement = (
            select(Commit)
            .where(Commit.repository_id == repository_id)
            .order_by(desc(Commit.committed_at))
            .limit(1)
        )
        return self.db.scalars(statement).first()

    def list_pending_commits(self, limit: int = 100) -> Sequence[Commit]:
        """
        Fetch commits that are awaiting downstream processing (status=PENDING).

        This is the primary query for Milestone 6 background workers. Workers
        call this method to obtain a batch of commits to process for AI
        summarisation, embeddings generation, and documentation creation.

        Uses ix_commits_status for O(log n) lookup by status value.

        The caller is responsible for transitioning commit status to PROCESSING
        immediately after fetching to prevent other workers from picking up the
        same batch (advisory locking is a Milestone 6 concern).

        Args:
            limit: Maximum batch size. Defaults to 100.

        Returns:
            Sequence of Commit ORM objects with status=PENDING.
        """
        statement = (
            select(Commit)
            .where(Commit.status == CommitStatus.PENDING)
            .order_by(Commit.committed_at)  # process oldest commits first
            .limit(limit)
        )
        return self.db.scalars(statement).all()

    def update_commit_status(
        self,
        commit: Commit,
        status: CommitStatus,
    ) -> Commit:
        """
        Update the processing status of a single Commit record.

        Used by Milestone 6 workers to transition commits through the
        PENDING → PROCESSING → COMPLETED | FAILED lifecycle.

        Args:
            commit: The Commit ORM object to update.
            status: The new CommitStatus value.

        Returns:
            The refreshed Commit ORM object.
        """
        commit.status = status
        self.db.commit()
        self.db.refresh(commit)
        return commit
