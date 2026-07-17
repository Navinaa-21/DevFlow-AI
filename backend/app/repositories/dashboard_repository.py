from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy import select, func, desc, case
from sqlalchemy.orm import Session
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.models.repository import Repository
from app.models.commit import Commit


class DashboardRepository:
    """
    Repository layer for querying aggregate statistics and activity across
    workspaces, repositories, and commits.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_user_workspace_ids(self, user_id: UUID) -> List[UUID]:
        """Fetch all workspace UUIDs that the given user belongs to."""
        statement = select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)
        return list(self.db.scalars(statement).all())

    def get_repository_stats(self, workspace_ids: List[UUID]) -> Dict[str, Any]:
        """
        Get aggregate repository and commit statistics across the specified workspaces.
        Uses single queries for aggregations to avoid N+1 queries.
        """
        if not workspace_ids:
            return {
                "total_repositories": 0,
                "active_repositories": 0,
                "archived_repositories": 0,
                "total_commits": 0,
                "commits_last_24h": 0,
                "commits_last_7d": 0,
                "last_sync_time": None
            }

        # 1. Fetch Repository Counts & last sync time
        repos_stmt = (
            select(
                func.count(Repository.id).label("total"),
                func.sum(case((Repository.is_active == True, 1), else_=0)).label("active"),
                func.max(Repository.last_synced_at).label("last_sync")
            )
            .where(Repository.workspace_id.in_(workspace_ids))
        )
        repos_res = self.db.execute(repos_stmt).first()
        total_repos = repos_res.total if repos_res and repos_res.total else 0
        active_repos = repos_res.active if repos_res and repos_res.active else 0
        archived_repos = total_repos - active_repos
        last_sync = repos_res.last_sync if repos_res else None

        # 2. Fetch Commits Aggregation (total, 24h, 7d)
        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(hours=24)
        week_ago = now - timedelta(days=7)

        commits_stmt = (
            select(
                func.count(Commit.id).label("total"),
                func.sum(case((Commit.committed_at >= day_ago, 1), else_=0)).label("last_24h"),
                func.sum(case((Commit.committed_at >= week_ago, 1), else_=0)).label("last_7d")
            )
            .join(Repository, Repository.id == Commit.repository_id)
            .where(Repository.workspace_id.in_(workspace_ids))
        )
        commits_res = self.db.execute(commits_stmt).first()
        total_commits = commits_res.total if commits_res and commits_res.total else 0
        commits_24h = commits_res.last_24h if commits_res and commits_res.last_24h else 0
        commits_7d = commits_res.last_7d if commits_res and commits_res.last_7d else 0

        return {
            "total_repositories": total_repos,
            "active_repositories": active_repos,
            "archived_repositories": archived_repos,
            "total_commits": total_commits,
            "commits_last_24h": commits_24h,
            "commits_last_7d": commits_7d,
            "last_sync_time": last_sync
        }

    def get_recent_activity(self, workspace_ids: List[UUID], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent commits across repositories in the given workspace IDs, ordered by committed_at DESC.
        Only fetches necessary columns.
        """
        if not workspace_ids:
            return []

        statement = (
            select(
                Commit.id,
                Commit.repository_id,
                Commit.github_commit_sha,
                Commit.short_sha,
                Commit.commit_message,
                Commit.committed_at,
                Commit.author_name,
                Commit.author_email,
                Commit.branch,
                Repository.name.label("repository_name")
            )
            .join(Repository, Repository.id == Commit.repository_id)
            .where(Repository.workspace_id.in_(workspace_ids))
            .order_by(desc(Commit.committed_at))
            .limit(limit)
        )
        results = self.db.execute(statement).all()
        activities = []
        for row in results:
            activities.append({
                "id": row.id,
                "repository_id": row.repository_id,
                "repository_name": row.repository_name,
                "commit_sha": row.github_commit_sha,
                "short_sha": row.short_sha,
                "commit_message": row.commit_message,
                "committed_at": row.committed_at,
                "author_name": row.author_name,
                "author_email": row.author_email,
                "branch": row.branch
            })
        return activities

    def get_workspaces_summaries(self, user_id: UUID) -> List[Dict[str, Any]]:
        """
        Get all workspaces the user belongs to, including repo counts, active/archived counts,
        total commits, and last_synced_at using aggregate queries to avoid N+1 queries.
        """
        # Fetch workspaces user belongs to
        workspaces_stmt = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
        )
        workspaces = self.db.scalars(workspaces_stmt).all()
        if not workspaces:
            return []

        workspace_ids = [w.id for w in workspaces]

        # 1. Fetch Repository Stats grouped by workspace_id
        repo_stats_stmt = (
            select(
                Repository.workspace_id,
                func.count(Repository.id).label("total_repos"),
                func.sum(case((Repository.is_active == True, 1), else_=0)).label("active_repos"),
                func.max(Repository.last_synced_at).label("last_sync")
            )
            .where(Repository.workspace_id.in_(workspace_ids))
            .group_by(Repository.workspace_id)
        )
        repo_stats = {row.workspace_id: row for row in self.db.execute(repo_stats_stmt).all()}

        # 2. Fetch Commit count grouped by workspace_id
        commit_stats_stmt = (
            select(
                Repository.workspace_id,
                func.count(Commit.id).label("total_commits")
            )
            .join(Commit, Commit.repository_id == Repository.id)
            .where(Repository.workspace_id.in_(workspace_ids))
            .group_by(Repository.workspace_id)
        )
        commit_stats = {row.workspace_id: row.total_commits for row in self.db.execute(commit_stats_stmt).all()}

        summaries = []
        for ws in workspaces:
            stats = repo_stats.get(ws.id)
            total_repos = stats.total_repos if stats else 0
            active_repos = stats.active_repos if stats and stats.active_repos else 0
            archived_repos = total_repos - active_repos
            last_sync = stats.last_sync if stats else None
            commits_count = commit_stats.get(ws.id, 0)

            summaries.append({
                "id": ws.id,
                "name": ws.name,
                "slug": ws.slug,
                "description": ws.description,
                "repository_count": total_repos,
                "active_repository_count": active_repos,
                "archived_repository_count": archived_repos,
                "total_commits": commits_count,
                "last_synced_at": last_sync
            })
        return summaries
