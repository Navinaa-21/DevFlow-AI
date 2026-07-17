import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.database import engine
from app.db.session import SessionLocal, get_db
from app.main import app
from app.models.base import Base
from app.models.enums import WorkspaceRole
from app.models.repository import Repository
from app.models.user import User
from app.models.webhook_event import WebhookEvent
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.schemas.repository import RepositoryCreateRequest
from app.services.auth_service import AuthService
from app.utils.webhook_signature import GitHubWebhookVerifier


@pytest.fixture(scope="module", autouse=True)
def init_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_user(db_session, email_suffix=None, full_name=None):
    email = f"{uuid.uuid4().hex[:8]}@example.com" if email_suffix is None else email_suffix
    user = User(full_name=full_name or "Test User", email=email, is_active=True, is_verified=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _token_for(db_session, user):
    return AuthService(db_session).generate_auth_tokens(user)["access_token"]


def _create_workspace(client, token, name=None, slug=None):
    response = client.post(
        "/workspaces",
        json={"name": name or "Sync Workspace", "slug": slug or f"sync-{uuid.uuid4().hex[:8]}", "description": "sync"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def test_manual_sync_updates_repository_metadata(client, db_session):
    owner = _create_user(db_session, email_suffix="sync-owner@example.com", full_name="Sync Owner")
    owner_token = _token_for(db_session, owner)
    workspace = _create_workspace(client, owner_token, name="Sync Workspace", slug=f"sync-ws-{uuid.uuid4().hex[:8]}")

    repository = client.post(
        f"/workspaces/{workspace['id']}/repositories",
        json={
            "name": "sync-repo",
            "provider": "GITHUB",
            "provider_repository_id": "7777",
            "clone_url": "https://github.com/test/sync-repo.git",
            "default_branch": "develop",
            "visibility": "private",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert repository.status_code == 201
    repo_id = repository.json()["id"]

    response = client.post(
        f"/repositories/{repo_id}/sync",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sync_status"] == "success"
    assert payload["default_branch"] == "main"
    assert payload["last_synced_at"] is not None


def test_repository_webhook_endpoint_stores_event_and_updates_repository(client, db_session):
    settings.GITHUB_WEBHOOK_SECRET = "test-secret"
    owner = _create_user(db_session, email_suffix="webhook-owner@example.com", full_name="Webhook Owner")
    owner_token = _token_for(db_session, owner)
    workspace = _create_workspace(client, owner_token, name="Webhook Workspace", slug=f"webhook-ws-{uuid.uuid4().hex[:8]}")

    repository = client.post(
        f"/workspaces/{workspace['id']}/repositories",
        json={
            "name": "webhook-repo",
            "provider": "GITHUB",
            "provider_repository_id": "8888",
            "clone_url": "https://github.com/test/webhook-repo.git",
            "default_branch": "main",
            "visibility": "private",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert repository.status_code == 201
    repo_id = repository.json()["id"]

    payload = {
        "action": "published",
        "repository": {
            "id": 8888,
            "name": "webhook-repo",
            "default_branch": "main",
            "archived": False,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    signature = GitHubWebhookVerifier(secret="test-secret").generate_signature(body)

    response = client.post(
        "/repositories/webhook",
        content=body,
        headers={
            "X-Hub-Signature-256": signature,
            "X-GitHub-Delivery": "delivery-123",
            "X-GitHub-Event": "repository",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"

    stored = db_session.query(WebhookEvent).filter(WebhookEvent.delivery_id == "delivery-123").first()
    assert stored is not None
    assert str(stored.repository_id) == repo_id

    refreshed = db_session.get(Repository, repo_id)
    assert refreshed is not None
    assert refreshed.name == "webhook-repo"
