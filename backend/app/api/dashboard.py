from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.db.session import get_db
from app.schemas.dashboard import DashboardStatsResponse
from app.repositories.dashboard_repository import DashboardRepository
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    status_code=status.HTTP_200_OK
)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> DashboardStatsResponse:
    dashboard_repo = DashboardRepository(db)
    stats = dashboard_repo.get_user_dashboard(current_user.id)
    
    return DashboardStatsResponse(**stats)
