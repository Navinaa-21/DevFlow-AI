from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    RecentActivityResponse,
    WorkspaceSummaryResponse,
)
from app.services.dashboard_service import DashboardService, DashboardPermissionError

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get dashboard summary stats",
    description="Retrieve aggregate counts of workspaces, repositories, and commits for workspaces the user has access to.",
)
def get_dashboard_summary(
    workspace_id: Optional[UUID] = Query(None, description="Optional workspace UUID filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    try:
        return service.get_summary(current_user, workspace_id)
    except DashboardPermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error)
        ) from error


@router.get(
    "/recent-activity",
    response_model=List[RecentActivityResponse],
    status_code=status.HTTP_200_OK,
    summary="Get recent repository activity",
    description="Retrieve a list of the most recent commits from repositories the user has access to.",
)
def get_recent_activity(
    workspace_id: Optional[UUID] = Query(None, description="Optional workspace UUID filter"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of activity items to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    try:
        return service.get_recent_activity(current_user, workspace_id, limit)
    except DashboardPermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error)
        ) from error


@router.get(
    "/workspaces",
    response_model=List[WorkspaceSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get dashboard workspaces summary",
    description="Retrieve details and repository metrics for all workspaces the user is a member of.",
)
def get_workspaces_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = DashboardService(db)
    return service.get_workspaces(current_user)
