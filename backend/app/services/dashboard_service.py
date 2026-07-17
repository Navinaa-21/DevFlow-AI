from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.user import User
from app.repositories.dashboard_repository import DashboardRepository


class DashboardServiceError(Exception):
    """Base exception for dashboard service errors."""
    pass


class DashboardPermissionError(DashboardServiceError):
    """Raised when user lacks permission to access workspace dashboard data."""
    pass


class DashboardService:
    """
    Service layer implementing authorization checks and business logic 
    for dashboard statistics and activities.
    """

    def __init__(self, db: Session):
        self.db = db
        self.repository = DashboardRepository(db)

    def get_summary(self, current_user: User, workspace_id: Optional[UUID] = None) -> dict:
        """
        Get aggregate stats across all workspaces of the user (or filter by one if provided).
        Validates membership before returning data.
        """
        user_workspace_ids = self.repository.get_user_workspace_ids(current_user.id)

        if workspace_id is not None:
            if workspace_id not in user_workspace_ids:
                raise DashboardPermissionError("You do not have access to this workspace.")
            active_workspace_ids = [workspace_id]
        else:
            active_workspace_ids = user_workspace_ids

        stats = self.repository.get_repository_stats(active_workspace_ids)
        return {
            "total_workspaces": len(user_workspace_ids) if workspace_id is None else 1,
            "repositories": stats
        }

    def get_recent_activity(self, current_user: User, workspace_id: Optional[UUID] = None, limit: int = 10) -> list:
        """
        Get recent commits across all workspaces of the user (or filter by one if provided).
        Validates membership before returning data.
        """
        user_workspace_ids = self.repository.get_user_workspace_ids(current_user.id)

        if workspace_id is not None:
            if workspace_id not in user_workspace_ids:
                raise DashboardPermissionError("You do not have access to this workspace.")
            active_workspace_ids = [workspace_id]
        else:
            active_workspace_ids = user_workspace_ids

        return self.repository.get_recent_activity(active_workspace_ids, limit=limit)

    def get_workspaces(self, current_user: User) -> list:
        """Get summary stats for all workspaces the user is a member of."""
        return self.repository.get_workspaces_summaries(current_user.id)
