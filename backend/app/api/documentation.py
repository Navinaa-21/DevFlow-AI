from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.commit import DocumentationResponse
from app.services.documentation_query_service import DocumentationQueryService
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

from app.schemas.documentation import DocumentationTocResponse, DocTocItem
from app.models.documentation import Documentation
from app.models.commit import Commit
from app.models.repository import Repository
from sqlalchemy import select

@router.get(
    "/toc",
    response_model=DocumentationTocResponse,
    status_code=status.HTTP_200_OK
)
def get_documentation_toc(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> DocumentationTocResponse:
    """
    Retrieves a list of recent commits that have generated documentation,
    to serve as the Table of Contents.
    """
    query_service = DocumentationQueryService(db)
    results = query_service.get_user_documentation_toc(current_user.id, limit)
    
    items = []
    for doc, commit, repo in results:
        items.append(DocTocItem(
            commit_id=commit.id,
            repo_name=repo.name,
            message=commit.message
        ))
        
    return DocumentationTocResponse(items=items)


@router.get(
    "/commits/{commit_id}/documentation",
    response_model=DocumentationResponse,
    status_code=status.HTTP_200_OK
)
def get_documentation_by_commit(
    commit_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> DocumentationResponse:
    """
    Retrieves the generated documentation update for a specific commit.

    Dependencies:
        - db (Session): Sync SQLAlchemy Session, injected via FastAPI dependency.
    """
    query_service = DocumentationQueryService(db)
    doc = query_service.get_user_documentation_by_commit_id(current_user.id, commit_id)
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Documentation for commit ID {commit_id} not found."
        )
        
    return doc
