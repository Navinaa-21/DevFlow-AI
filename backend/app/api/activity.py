from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.schemas.activity import ActivityFeedResponse, ActivityItemResponse
from app.repositories.activity_repository import ActivityRepository
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

@router.get(
    "/",
    response_model=ActivityFeedResponse,
    status_code=status.HTTP_200_OK
)
def get_activity_feed(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ActivityFeedResponse:
    activity_repo = ActivityRepository(db)
    activities = activity_repo.get_user_activity(current_user.id, limit)
        
    return ActivityFeedResponse(activities=activities)
