import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.db.database import engine
from app.db.session import SessionLocal, get_db
from app.main import app
from app.models.base import Base
from app.models.enums import CommitStatus
from app.models.user import User
from app.models.repository import Repository
from app.models.webhook_event import WebhookEvent
from app.models.commit import Commit
from app.services.auth_service import AuthService


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


def _create_user(db_session):
    email = f"{uuid.uuid4().hex[:8]}@example.com"
    user = User(full_name="Analytics User", email=email, is_active=True, is_verified=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _token_for(db_session, user):
    return AuthService(db_session).generate_auth_tokens(user)["access_token"]


def _create_workspace(client, token, name="WS"):
    response = client.post(
        "/workspaces",
        json={"name": name, "slug": f"slug-{uuid.uuid4().hex[:8]}", "description": "desc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def _connect_repo(client, token, workspace_id, name, is_active=True, last_synced_at=None, provider_id=None):
    prov_id = provider_id or f"p-{uuid.uuid4().hex[:8]}"
    response = client.post(
        f"/workspaces/{workspace_id}/repositories",
        json={
            "name": name,
            "provider": "GITHUB",
            "provider_repository_id": prov_id,
            "clone_url": f"https://github.com/test/{name}.git",
            "default_branch": "main",
            "visibility": "private",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    repo_json = response.json()
    return repo_json["id"]


def _create_commit(db_session, repository_id, sha, committed_at, message="Commit message"):
    # First create dummy webhook event because commit requires a webhook_event_id
    event = WebhookEvent(
        repository_id=repository_id,
        event_type="push",
        delivery_id=f"del-{uuid.uuid4().hex[:8]}",
        payload={},
        processed=True,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)

    commit = Commit(
        repository_id=repository_id,
        webhook_event_id=event.id,
        github_commit_sha=sha,
        short_sha=sha[:8],
        commit_message=message,
        commit_url=f"https://github.com/test/repo/commit/{sha}",
        committed_at=committed_at,
        branch="main",
        author_name="Developer",
        author_email="dev@example.com",
        raw_payload={},
        status=CommitStatus.PENDING,
    )
    db_session.add(commit)
    db_session.commit()
    db_session.refresh(commit)
    return commit


def test_repository_analytics_aggregates(client, db_session):
    """Verify core aggregate calculation correctness (repos, commits, time-ranges, last sync)."""
    user = _create_user(db_session)
    token = _token_for(db_session, user)
    ws = _create_workspace(client, token, name="WS 1")

    now = datetime.now(timezone.utc)
    
    # 1. Create two repositories: Repo A (Active), Repo B (Archived/Inactive)
    repo_a_id = _connect_repo(client, token, ws["id"], "repo-a", provider_id="1001")
    repo_b_id = _connect_repo(client, token, ws["id"], "repo-b", provider_id="1002")

    # Manually configure repository states (archive / sync timestamp) in DB
    db_repo_a = db_session.get(Repository, repo_a_id)
    db_repo_a.is_active = True
    db_repo_a.last_synced_at = now - timedelta(hours=2) # sync time 2 hours ago

    db_repo_b = db_session.get(Repository, repo_b_id)
    db_repo_b.is_active = False # Archived
    db_repo_b.last_synced_at = now - timedelta(hours=5)

    db_session.commit()

    # 2. Add commits
    # Commit 1: committed 1 hour ago (within 24h, within 7d)
    _create_commit(db_session, repo_a_id, "sha1111111111111111111111111111111111111", now - timedelta(hours=1))
    
    # Commit 2: committed 2 days ago (older than 24h, within 7d)
    _create_commit(db_session, repo_a_id, "sha2222222222222222222222222222222222222", now - timedelta(days=2))

    # Commit 3: committed 10 days ago (older than 7d)
    _create_commit(db_session, repo_a_id, "sha3333333333333333333333333333333333333", now - timedelta(days=10))

    # Commit 4: committed 3 hours ago for Repo B (within 24h, within 7d)
    _create_commit(db_session, repo_b_id, "sha4444444444444444444444444444444444444", now - timedelta(hours=3))

    # Query dashboard summary
    response = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()

    assert data["total_workspaces"] == 1
    repos_data = data["repositories"]
    
    assert repos_data["total_repositories"] == 2
    assert repos_data["active_repositories"] == 1
    assert repos_data["archived_repositories"] == 1
    assert repos_data["total_commits"] == 4
    assert repos_data["commits_last_24h"] == 2 # Commit 1 & 4
    assert repos_data["commits_last_7d"] == 3  # Commit 1, 2, & 4
    
    # Last sync time is the maximum of repo sync timestamps (Repo A: now - 2 hours)
    sync_time_str = repos_data["last_sync_time"]
    assert sync_time_str is not None
    # Parse sync time and assert it matches Repo A sync time (within a small delta)
    parsed_sync_time = datetime.fromisoformat(sync_time_str.replace("Z", "+00:00"))
    expected_sync_time = (now - timedelta(hours=2)).replace(microsecond=0)
    assert abs((parsed_sync_time - expected_sync_time).total_seconds()) < 5

    # Check GET /dashboard/recent-activity returns correct list
    response = client.get("/dashboard/recent-activity?limit=5", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    activities = response.json()
    assert len(activities) == 4
    # Check that they are sorted DESC by committed_at (newest first: Commit 1, then Commit 4, then Commit 2, then Commit 3)
    shas = [act["commit_sha"] for act in activities]
    assert shas[0].startswith("sha1")
    assert shas[1].startswith("sha4")
    assert shas[2].startswith("sha2")
    assert shas[3].startswith("sha3")


def test_dashboard_multiple_workspaces_isolation(client, db_session):
    """Verify workspace filtering and isolation (user only sees data for queried workspace or authorized workspaces)."""
    user1 = _create_user(db_session)
    token1 = _token_for(db_session, user1)
    ws1 = _create_workspace(client, token1, name="Workspace 1")
    ws2 = _create_workspace(client, token1, name="Workspace 2")

    # Connect Repo 1 to WS1
    repo1_id = _connect_repo(client, token1, ws1["id"], "repo-ws1", provider_id="2001")
    # Connect Repo 2 to WS2
    repo2_id = _connect_repo(client, token1, ws2["id"], "repo-ws2", provider_id="2002")

    # User 2 in a different workspace
    user2 = _create_user(db_session)
    token2 = _token_for(db_session, user2)
    ws3 = _create_workspace(client, token2, name="Workspace 3")
    repo3_id = _connect_repo(client, token2, ws3["id"], "repo-ws3", provider_id="2003")

    # Add commits to each repo
    now = datetime.now(timezone.utc)
    _create_commit(db_session, repo1_id, "sha1111", now)
    _create_commit(db_session, repo2_id, "sha2222", now)
    _create_commit(db_session, repo3_id, "sha3333", now)

    # 1. User 1 queries summary aggregated across all workspaces (WS1 + WS2)
    response = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {token1}"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_workspaces"] == 2
    assert data["repositories"]["total_repositories"] == 2
    assert data["repositories"]["total_commits"] == 2 # repo1 and repo2

    # 2. User 1 queries summary filtered by WS 1 only
    response = client.get(f"/dashboard/summary?workspace_id={ws1['id']}", headers={"Authorization": f"Bearer {token1}"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_workspaces"] == 1
    assert data["repositories"]["total_repositories"] == 1
    assert data["repositories"]["total_commits"] == 1 # repo1 only

    # 3. User 1 queries recent activity filtered by WS 2 only
    response = client.get(f"/dashboard/recent-activity?workspace_id={ws2['id']}", headers={"Authorization": f"Bearer {token1}"})
    assert response.status_code == 200
    activities = response.json()
    assert len(activities) == 1
    assert activities[0]["commit_sha"] == "sha2222"
