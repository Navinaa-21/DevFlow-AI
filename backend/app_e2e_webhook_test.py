import os
import json
import uuid
import hmac
import hashlib
from datetime import datetime, timezone
import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import SessionLocal
from app.models.repository import Repository
from app.models.enums import RepositoryProvider
from app.models.workspace import Workspace
from app.models.user import User
from app.core.config import settings
from app.models.webhook_event import WebhookEvent
from app.models.commit import Commit

# Ensure webhook secret is set for testing
settings.GITHUB_WEBHOOK_SECRET = "test_e2e_secret"

client = TestClient(app)

def generate_signature(payload: bytes, secret: str) -> str:
    mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    return f"sha256={mac.hexdigest()}"

def setup_test_data(db: Session) -> uuid.UUID:
    """Creates a user, workspace, and repository for testing."""
    user = User(
        email=f"test_{uuid.uuid4()}@example.com",
        full_name=f"testuser_{uuid.uuid4().hex[:8]}",
        is_active=True,
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create test workspace
    workspace = Workspace(
        name="E2E Test Workspace",
        slug=f"e2e-test-{uuid.uuid4().hex[:8]}"
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    # Create test repository
    repository = Repository(
        workspace_id=workspace.id,
        provider=RepositoryProvider.GITHUB,
        provider_repo_id=str(uuid.uuid4()),
        name="test-repo",
        full_name="testuser/test-repo",
        repo_url="https://github.com/testuser/test-repo",
        is_active=True
    )
    db.add(repository)
    db.commit()
    db.refresh(repository)

    return repository.id


def run_e2e_tests():
    from app.db.database import engine
    from app.models.base import Base
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        repo_id = setup_test_data(db)
        print(f"Test Repository ID: {repo_id}")

        # Helper to construct request
        def send_webhook(event_type: str, delivery_id: str, payload_dict: dict, modify_signature: bool = False):
            payload_bytes = json.dumps(payload_dict).encode("utf-8")
            signature = generate_signature(payload_bytes, settings.GITHUB_WEBHOOK_SECRET)
            if modify_signature:
                signature = "sha256=invalid"
            
            headers = {
                "X-Hub-Signature-256": signature,
                "X-GitHub-Delivery": delivery_id,
                "X-GitHub-Event": event_type,
                "Content-Type": "application/json"
            }
            return client.post(f"/webhooks/github/{repo_id}", content=payload_bytes, headers=headers)

        # ---------------------------------------------------------
        # Scenario 1: Valid GitHub Push Event
        # ---------------------------------------------------------
        print("Scenario 1: Valid GitHub Push Event")
        valid_delivery_id = str(uuid.uuid4())
        valid_payload = {
            "ref": "refs/heads/main",
            "commits": [
                {
                    "id": f"sha1_{uuid.uuid4().hex}",
                    "message": "First commit",
                    "timestamp": "2023-01-01T12:00:00Z",
                    "author": {"name": "Alice", "email": "alice@example.com"}
                },
                {
                    "id": f"sha2_{uuid.uuid4().hex}",
                    "message": "Second commit",
                    "timestamp": "2023-01-01T12:05:00Z",
                    "author": {"name": "Bob", "email": "bob@example.com"}
                }
            ]
        }
        
        response = send_webhook("push", valid_delivery_id, valid_payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        assert "Processed 2 commits" in response.json()["message"]
        
        # Verify DB
        event = db.query(WebhookEvent).filter_by(delivery_id=valid_delivery_id).first()
        assert event is not None
        assert event.processing_status.value == "PROCESSED"
        
        commits = db.query(Commit).filter_by(webhook_event_id=event.id).all()
        assert len(commits) == 2
        print("=> PASS")

        # ---------------------------------------------------------
        # Scenario 2: Invalid Signature
        # ---------------------------------------------------------
        print("Scenario 2: Invalid Signature")
        response = send_webhook("push", str(uuid.uuid4()), valid_payload, modify_signature=True)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("=> PASS")

        # ---------------------------------------------------------
        # Scenario 3: Duplicate Delivery
        # ---------------------------------------------------------
        print("Scenario 3: Duplicate Delivery")
        response = send_webhook("push", valid_delivery_id, valid_payload)
        assert response.status_code == 200
        assert "Already processed" in response.json()["message"]
        
        # Ensure no duplicates in DB
        events = db.query(WebhookEvent).filter_by(delivery_id=valid_delivery_id).all()
        assert len(events) == 1
        print("=> PASS")

        # ---------------------------------------------------------
        # Scenario 4: Unsupported GitHub Event
        # ---------------------------------------------------------
        print("Scenario 4: Unsupported GitHub Event")
        unsupported_delivery = str(uuid.uuid4())
        response = send_webhook("issues", unsupported_delivery, {"action": "opened"})
        assert response.status_code == 200
        assert "Ignored" in response.json()["message"]
        
        # Verify DB
        event = db.query(WebhookEvent).filter_by(delivery_id=unsupported_delivery).first()
        assert event.processing_status.value == "IGNORED"
        print("=> PASS")

        # ---------------------------------------------------------
        # Scenario 5: Malformed Payload
        # ---------------------------------------------------------
        print("Scenario 5: Malformed Payload")
        malformed_delivery = str(uuid.uuid4())
        malformed_bytes = b"invalid json data"
        signature = generate_signature(malformed_bytes, settings.GITHUB_WEBHOOK_SECRET)
        headers = {
            "X-Hub-Signature-256": signature,
            "X-GitHub-Delivery": malformed_delivery,
            "X-GitHub-Event": "push",
            "Content-Type": "application/json"
        }
        response = client.post(f"/webhooks/github/{repo_id}", content=malformed_bytes, headers=headers)
        assert response.status_code == 400
        print("=> PASS")

        # ---------------------------------------------------------
        # Scenario 6: Bulk Commit Push
        # ---------------------------------------------------------
        print("Scenario 6: Bulk Commit Push")
        bulk_delivery = str(uuid.uuid4())
        bulk_commits = []
        for i in range(50):
            bulk_commits.append({
                "id": f"bulk_{i}_{uuid.uuid4().hex}",
                "message": f"Bulk commit {i}",
                "author": {"name": "Bot"}
            })
        
        bulk_payload = {"ref": "refs/heads/bulk", "commits": bulk_commits}
        response = send_webhook("push", bulk_delivery, bulk_payload)
        assert response.status_code == 200
        assert "Processed 50 commits" in response.json()["message"]
        
        # Verify DB
        event = db.query(WebhookEvent).filter_by(delivery_id=bulk_delivery).first()
        assert event.processing_status.value == "PROCESSED"
        count = db.query(Commit).filter_by(webhook_event_id=event.id).count()
        assert count == 50
        print("=> PASS")

        # ---------------------------------------------------------
        # Scenario 7: Verify PostgreSQL
        # ---------------------------------------------------------
        print("Scenario 7: Verify PostgreSQL DB State")
        # We implicitly verified this during Scenarios 1 and 6, but we can do a final fetch
        all_events = db.query(WebhookEvent).filter_by(repository_id=repo_id).all()
        assert len(all_events) == 3 # Valid Push, Unsupported Event, Bulk Push
        
        commits = db.query(Commit).filter_by(repository_id=repo_id).all()
        assert len(commits) == 52 # 2 from Valid Push + 50 from Bulk Push
        print("=> PASS")

        # ---------------------------------------------------------
        # Scenario 8: Swagger Validation
        # ---------------------------------------------------------
        print("Scenario 8: Swagger Validation")
        openapi_resp = client.get("/openapi.json")
        assert openapi_resp.status_code == 200
        openapi = openapi_resp.json()
        assert "/webhooks/github/{repository_id}" in openapi["paths"]
        assert "post" in openapi["paths"]["/webhooks/github/{repository_id}"]
        print("=> PASS")

        print("\nAll End-to-End Tests Passed Successfully!")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_e2e_tests()
