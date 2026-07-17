from uuid import UUID
from fastapi import APIRouter, Request, Header, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.config import settings
from app.db.session import get_db
from app.repositories.commit_repository import CommitRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.webhook_repository import WebhookRepository
from app.services.webhook_service import WebhookService
from app.utils.webhook_signature import GitHubWebhookVerifier


router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class WebhookResponse(BaseModel):
    status: str
    message: str


@router.post("/github/{repository_id}", response_model=WebhookResponse, status_code=status.HTTP_200_OK)
async def github_webhook(
    repository_id: UUID,
    request: Request,
    x_hub_signature_256: str = Header(..., alias="X-Hub-Signature-256"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    db: Session = Depends(get_db)
):
    """
    GitHub Webhook Ingestion Endpoint.
    
    Receives push events from GitHub, verifies their HMAC signature, and processes
    the commits for ingestion into the system.
    
    The repository_id must be provided in the URL path. This URL should be generated
    and registered with GitHub when a repository is connected.
    """
    # 2. Read the raw request body using await request.body()
    payload_bytes = await request.body()
    
    # Initialize dependencies
    webhook_repo = WebhookRepository(db)
    commit_repo = CommitRepository(db)
    repository_repo = RepositoryRepository(db)
    verifier = GitHubWebhookVerifier(secret=settings.GITHUB_WEBHOOK_SECRET)
    
    service = WebhookService(
        webhook_repo=webhook_repo,
        commit_repo=commit_repo,
        repository_repo=repository_repo,
        verifier=verifier
    )
    
    # 4. Pass the raw payload bytes and headers to WebhookService
    result = service.process_github_webhook(
        repository_id=repository_id,
        payload_bytes=payload_bytes,
        signature_header=x_hub_signature_256,
        delivery_id=x_github_delivery,
        event_type=x_github_event
    )
    
    return result
