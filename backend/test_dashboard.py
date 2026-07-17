import uuid
import pytest
from fastapi.testclient import TestClient

from app.db.database import engine
from app.db.session import SessionLocal, get_db
from app.main import app
from app.models.base import Base
from app.models.user import User
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


def _create_user(db_session, email=None):
    email_val = email or f"{uuid.uuid4().hex[:8]}@example.com"
    user = User(full_name="Dashboard User", email=email_val, is_active=True, is_verified=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _token_for(db_session, user):
    return AuthService(db_session).generate_auth_tokens(user)["access_token"]


def _create_workspace(client, token, name="Test WS"):
    response = client.post(
        "/workspaces",
        json={"name": name, "slug": f"slug-{uuid.uuid4().hex[:8]}", "description": "test desc"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    return response.json()


def test_jwt_protection_on_dashboard_endpoints(client):
    """Verify that requests without a valid JWT return 401 Unauthorized."""
    endpoints = ["/dashboard/summary", "/dashboard/recent-activity", "/dashboard/workspaces"]
    for url in endpoints:
        response = client.get(url)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]


def test_empty_workspace_returns_zeroes(client, db_session):
    """Verify stats return zeroed counts for a user with a workspace containing no repos."""
    user = _create_user(db_session)
    token = _token_for(db_session, user)
    _create_workspace(client, token, name="Empty Workspace")

    response = client.get("/dashboard/summary", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_workspaces"] == 1
    
    repos_data = data["repositories"]
    assert repos_data["total_repositories"] == 0
    assert repos_data["active_repositories"] == 0
    assert repos_data["archived_repositories"] == 0
    assert repos_data["total_commits"] == 0
    assert repos_data["commits_last_24h"] == 0
    assert repos_data["commits_last_7d"] == 0
    assert repos_data["last_sync_time"] is None


def test_unauthorized_workspace_filter_raises_403(client, db_session):
    """Verify that filtering by a workspace the user does not belong to returns 403 Forbidden."""
    user1 = _create_user(db_session)
    token1 = _token_for(db_session, user1)
    ws1 = _create_workspace(client, token1, name="User 1 Workspace")

    user2 = _create_user(db_session)
    token2 = _token_for(db_session, user2)

    # User 2 tries to filter dashboard by User 1's workspace ID
    response = client.get(
        f"/dashboard/summary?workspace_id={ws1['id']}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert response.status_code == 403
    assert "access to this workspace" in response.json()["detail"]

    # User 2 tries to query recent activity for User 1's workspace ID
    response = client.get(
        f"/dashboard/recent-activity?workspace_id={ws1['id']}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert response.status_code == 403
    assert "access to this workspace" in response.json()["detail"]


def test_dashboard_workspaces_list(client, db_session):
    """Verify GET /dashboard/workspaces lists only workspaces the user belongs to."""
    user1 = _create_user(db_session)
    token1 = _token_for(db_session, user1)
    ws1 = _create_workspace(client, token1, name="User 1 WS 1")
    ws2 = _create_workspace(client, token1, name="User 1 WS 2")

    user2 = _create_user(db_session)
    token2 = _token_for(db_session, user2)
    ws3 = _create_workspace(client, token2, name="User 2 WS")

    # User 1 query
    response1 = client.get("/dashboard/workspaces", headers={"Authorization": f"Bearer {token1}"})
    assert response1.status_code == 200
    data1 = response1.json()
    assert len(data1) == 2
    slugs = [w["slug"] for w in data1]
    assert ws1["slug"] in slugs
    assert ws2["slug"] in slugs
    assert ws3["slug"] not in slugs

    # User 2 query
    response2 = client.get("/dashboard/workspaces", headers={"Authorization": f"Bearer {token2}"})
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2) == 1
    assert data2[0]["slug"] == ws3["slug"]
