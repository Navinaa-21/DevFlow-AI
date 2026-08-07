import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.github_service import GithubService
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.repository import RepositoryResponse

router = APIRouter()

@router.get("/repositories", response_model=List[Dict[str, Any]])
def list_connectable_repositories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches all repositories available on GitHub for the user,
    excluding those already connected to DevFlow AI.
    """
    github_service = GithubService(db, current_user)
    repo_repo = RepositoryRepository(db)
    
    # 1. Fetch from GitHub
    github_repos = github_service.fetch_user_repositories()
    
    # 2. Fetch locally connected repos for this user
    local_repos = repo_repo.get_by_user(current_user.id)
    connected_github_ids = {repo.github_repo_id for repo in local_repos}
    
    # 3. Filter out connected repos and map needed fields
    available_repos = []
    for repo in github_repos:
        if repo["id"] not in connected_github_ids:
            available_repos.append({
                "github_repo_id": repo["id"],
                "owner": repo["owner"]["login"],
                "name": repo["name"],
                "private": repo["private"],
                "default_branch": repo["default_branch"],
                "clone_url": repo["clone_url"],
                "html_url": repo["html_url"]
            })
            
    return available_repos


@router.post("/connect/{github_repo_id}", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
def connect_github_repository(
    github_repo_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Connects a GitHub repository to DevFlow AI and establishes a webhook.
    """
    github_service = GithubService(db, current_user)
    repo_repo = RepositoryRepository(db)
    
    # 1. Verify if it's already connected
    existing_repo = repo_repo.get_by_github_repo_id(github_repo_id)
    if existing_repo:
        if existing_repo.user_id is not None and existing_repo.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Repository is already connected to another account."
            )
            
        # Verify ownership & admin permissions on GitHub
        repo_meta = github_service.fetch_repository_metadata(github_repo_id)
        if not repo_meta.get("permissions", {}).get("admin", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must have admin permissions on the repository to connect it."
            )
            
        # Establish webhook on GitHub
        base = str(request.base_url).rstrip("/")
        webhook_url = f"{base}/webhooks/github"
        owner = repo_meta["owner"]["login"]
        name = repo_meta["name"]
        
        try:
            github_service.create_webhook(owner, name, webhook_url)
        except Exception:
            # If webhook already exists, skip
            pass
            
        # Assign user and enable webhook in database
        existing_repo.user_id = current_user.id
        existing_repo.webhook_enabled = True
        db.commit()
        db.refresh(existing_repo)
        return existing_repo
        
    # 2. Fetch metadata & verify ownership/admin
    repo_meta = github_service.fetch_repository_metadata(github_repo_id)
    if not repo_meta.get("permissions", {}).get("admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must have admin permissions on the repository to connect it."
        )
        
    # 3. Construct webhook URL
    base = str(request.base_url).rstrip("/")
    webhook_url = f"{base}/webhooks/github"
    
    # 4. Create Webhook on GitHub
    owner = repo_meta["owner"]["login"]
    name = repo_meta["name"]
    github_service.create_webhook(owner, name, webhook_url)
    
    # 5. Persist to local database
    new_repo = repo_repo.create_repository(
        github_repo_id=github_repo_id,
        owner=owner,
        name=name,
        clone_url=repo_meta["clone_url"],
        default_branch=repo_meta["default_branch"],
        webhook_enabled=True,
        user_id=current_user.id
    )
    
    return new_repo


@router.delete("/disconnect/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_github_repository(
    repository_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Disconnects a repository by removing its webhook from GitHub and disabling it locally.
    Maintains history in the DB.
    """
    repo_repo = RepositoryRepository(db)
    github_service = GithubService(db, current_user)
    
    # 1. Verify ownership locally
    repo = repo_repo.get_user_repository(current_user.id, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or access denied."
        )
        
    # 2. Construct webhook URL to identify it on GitHub
    base = str(request.base_url).rstrip("/")
    webhook_url = f"{base}/webhooks/github"
    
    # 3. Delete webhook on GitHub
    github_service.delete_webhook(repo.owner, repo.name, webhook_url)
    
    # 4. Disable locally to retain history
    repo_repo.update_user_repository(current_user.id, repository_id, webhook_enabled=False)
    
    return None
