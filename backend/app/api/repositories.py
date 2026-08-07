from typing import List
import random
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import get_db
from app.schemas.repository import RepositoryResponse, RepositoriesListResponse, RepositoryCreate
from app.models.repository import Repository
from app.models.user import User
from app.core.security import get_current_user
from app.repositories.repository_repository import RepositoryRepository

router = APIRouter()

@router.post(
    "/",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED
)
def create_repository(
    repo_in: RepositoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> RepositoryResponse:
    # Generate mock github repo id for MVP
    mock_github_id = random.randint(1000000, 9999999)
    
    new_repo = Repository(
        github_repo_id=mock_github_id,
        owner=repo_in.owner,
        name=repo_in.name,
        clone_url=repo_in.clone_url,
        default_branch=repo_in.default_branch,
        webhook_enabled=repo_in.webhook_enabled,
        user_id=current_user.id
    )
    
    db.add(new_repo)
    db.commit()
    db.refresh(new_repo)
    return new_repo

@router.get(
    "/",
    response_model=RepositoriesListResponse,
    status_code=status.HTTP_200_OK
)
def list_repositories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> RepositoriesListResponse:
    stmt = select(Repository).where(Repository.user_id == current_user.id).offset(skip).limit(limit)
    repos = db.execute(stmt).scalars().all()
    
    total_stmt = select(Repository).where(Repository.user_id == current_user.id)
    total_count = len(db.execute(total_stmt).scalars().all())
    
    return RepositoriesListResponse(
        repositories=repos,
        total_count=total_count
    )

@router.get(
    "/{repo_name}",
    response_model=RepositoryResponse,
    status_code=status.HTTP_200_OK
)
def get_repository_details(
    repo_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> RepositoryResponse:
    repo_repo = RepositoryRepository(db)
    repo = repo_repo.get_user_repository_by_name(current_user.id, repo_name)
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_name} not found."
        )
        
    return repo

@router.delete(
    "/{repo_name}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_repository(
    repo_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    repo_repo = RepositoryRepository(db)
    repo = repo_repo.get_user_repository_by_name(current_user.id, repo_name)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_name} not found."
        )
    repo_repo.delete(repo.id)
    return None

@router.put(
    "/{repo_name}",
    response_model=RepositoryResponse,
    status_code=status.HTTP_200_OK
)
def update_repository(
    repo_name: str,
    repo_in: RepositoryCreate, # Using RepositoryCreate for simplicity as per MVP style
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> RepositoryResponse:
    repo_repo = RepositoryRepository(db)
    repo = repo_repo.get_user_repository_by_name(current_user.id, repo_name)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_name} not found."
        )
    
    updated_repo = repo_repo.update(
        repo.id,
        owner=repo_in.owner,
        name=repo_in.name,
        clone_url=repo_in.clone_url,
        default_branch=repo_in.default_branch,
        webhook_enabled=repo_in.webhook_enabled
    )
    return updated_repo
