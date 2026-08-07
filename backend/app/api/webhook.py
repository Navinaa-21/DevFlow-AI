from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.webhook_service import WebhookService
from app.services.commit_service import CommitService

router = APIRouter()


@router.post(
    "/webhooks/github",
    status_code=status.HTTP_200_OK
)
async def github_webhook_handler(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
) -> dict:
    """
    Receives push event notifications from GitHub webhooks, verifies payload authenticity,
    persists new commits, and triggers the AI generation service asynchronously in the background.

    Dependencies:
        - request (Request): FastAPI request wrapper. Used to retrieve raw body bytes and headers.
        - background_tasks (BackgroundTasks): FastAPI BackgroundTasks runner. Used to trigger the AI generation pipeline without blocking.
        - db (Session): Sync SQLAlchemy Session, injected via FastAPI dependency. Used for database operations.
    """
    # 1. Retrieve the raw body and signature header
    payload_bytes = await request.body()
    signature_header = request.headers.get("x-hub-signature-256")
    
    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Signature header is missing."
        )

    # 2. Parse the request payload to JSON format
    try:
        payload_json = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload."
        )

    # 3. Call WebhookService to verify signature and persist commits
    webhook_service = WebhookService(db)
    try:
        commits = webhook_service.process_webhook_payload(
            payload_bytes=payload_bytes,
            signature_header=signature_header,
            payload_json=payload_json
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing error: {str(e)}"
        )

    # 4. Pass commits to CommitService to run in the background
    if commits:
        commit_service = CommitService(db)
        background_tasks.add_task(commit_service.handle_new_commits, commits)

    # 5. Return status result payload
    return {
        "status": "success",
        "processed_commits": len(commits)
    }
