from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.commit import CommitResponse
from app.repositories.commit_repository import CommitRepository
from app.services.commit_query_service import CommitQueryService
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()


@router.get(
    "/",
    response_model=List[CommitResponse],
    status_code=status.HTTP_200_OK
)
def list_processed_commits(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[CommitResponse]:
    """
    Retrieves a list of processed commits, along with their generated summaries and docs.

    Dependencies:
        - db (Session): Sync SQLAlchemy Session, injected via FastAPI dependency.
    """
    commit_repo = CommitRepository(db)
    return commit_repo.get_user_commits(user_id=current_user.id, limit=limit)


@router.get(
    "/{commit_id}",
    response_model=CommitResponse,
    status_code=status.HTTP_200_OK
)
def get_commit_details(
    commit_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> CommitResponse:
    """
    Retrieves details of a specific commit by its unique UUID,
    including its generated summary and related AI generation statuses.

    Dependencies:
        - db (Session): Sync SQLAlchemy Session, injected via FastAPI dependency.
    """
    query_service = CommitQueryService(db)
    commit = query_service.get_user_commit_with_generations(user_id=current_user.id, commit_id=commit_id)
    
    if not commit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commit with ID {commit_id} not found."
        )
        
    return commit

@router.get(
    "/repo/{repo_name}",
    response_model=List[CommitResponse],
    status_code=status.HTTP_200_OK
)
def get_commits_by_repo(
    repo_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[CommitResponse]:
    """
    Retrieves a list of commits belonging to a specific repository by name.
    """
    from app.repositories.repository_repository import RepositoryRepository
    from app.models.commit import Commit
    from sqlalchemy import select
    
    repo_repo = RepositoryRepository(db)
    repo = repo_repo.get_user_repository_by_name(current_user.id, repo_name)
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_name} not found."
        )
        
    commits_stmt = select(Commit).where(Commit.repository_id == repo.id).order_by(Commit.committed_at.desc())
    commits = db.execute(commits_stmt).scalars().all()
    
    return commits
