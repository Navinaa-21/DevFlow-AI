from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(schema: UserCreate, db: Session = Depends(get_db)):
    service = UserService(db)
    return service.create_user(schema)


@router.get("/", response_model=List[UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    sort_by: Optional[str] = None,
    db: Session = Depends(get_db)
):
    service = UserService(db)
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if is_verified is not None:
        filters["is_verified"] = is_verified
    return service.list_users(skip=skip, limit=limit, filters=filters, search=search, sort_by=sort_by)


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(user_id: UUID, db: Session = Depends(get_db)):
    service = UserService(db)
    return service.get_user_by_id(user_id)


@router.get("/by-email/{email}", response_model=UserResponse)
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    service = UserService(db)
    return service.get_user_by_email(email)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: UUID, schema: UserUpdate, db: Session = Depends(get_db)):
    service = UserService(db)
    return service.update_user(user_id, schema)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, db: Session = Depends(get_db)):
    service = UserService(db)
    service.delete_user(user_id)
    return None
