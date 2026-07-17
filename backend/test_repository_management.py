import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.database import engine
from app.db.session import SessionLocal, get_db
from app.main import app
from app.models.base import Base
from app.models.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
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
    payload = {
        "name": name or "Test Workspace",
        "slug": slug or f"ws-{uuid.uuid4().hex[:8]}",
        "description": "Test workspace",
    }
    response = client.post("/workspaces", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 201
    return response.json()


def _add_member(db_session, workspace_id, user_id, role):
    membership = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role)
    db_session.add(membership)
    db_session.commit()


def test_create_repository_successfully(client, db_session):
    owner = _create_user(db_session, email_suffix="repo-owner@example.com", full_name="Repository Owner")
    owner_token = _token_for(db_session, owner)
    workspace = _create_workspace(client, owner_token, name="Repo Workspace", slug=f"repo-ws-{uuid.uuid4().hex[:8]}")

    response = client.post(
        f"/workspaces/{workspace['id']}/repositories",
        json={
            "name": "demo-repo",
            "provider": "GITHUB",
            "provider_repository_id": "1001",
            "clone_url": "https://github.com/test/demo-repo.git",
            "default_branch": "main",
            "visibility": "private",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "demo-repo"
    assert payload["provider"] == "GITHUB"
    assert payload["visibility"] == "private"


def test_duplicate_repository_rejected(client, db_session):
    owner = _create_user(db_session, email_suffix="repo-owner-dup@example.com", full_name="Repository Owner Dup")
    owner_token = _token_for(db_session, owner)
    workspace = _create_workspace(client, owner_token, name="Dup Workspace", slug=f"dup-ws-{uuid.uuid4().hex[:8]}")

    first = client.post(
        f"/workspaces/{workspace['id']}/repositories",
        json={
            "name": "dup-repo",
            "provider": "GITHUB",
            "provider_repository_id": "2001",
            "clone_url": "https://github.com/test/dup-repo.git",
            "default_branch": "main",
            "visibility": "private",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert first.status_code == 201

    second = client.post(
        f"/workspaces/{workspace['id']}/repositories",
        json={
            "name": "dup-repo-2",
            "provider": "GITHUB",
            "provider_repository_id": "2001",
            "clone_url": "https://github.com/test/dup-repo-2.git",
            "default_branch": "main",
            "visibility": "private",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert second.status_code == 409


def test_list_and_get_repository(client, db_session):
    owner = _create_user(db_session, email_suffix="repo-owner-list@example.com", full_name="Repository Owner List")
    owner_token = _token_for(db_session, owner)
    workspace = _create_workspace(client, owner_token, name="List Workspace", slug=f"list-ws-{uuid.uuid4().hex[:8]}")

    created = client.post(
        f"/workspaces/{workspace['id']}/repositories",
        json={
            "name": "list-repo",
            "provider": "GITHUB",
            "provider_repository_id": "3001",
            "clone_url": "https://github.com/test/list-repo.git",
            "default_branch": "main",
            "visibility": "public",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 201
    repo_id = created.json()["id"]

    listed = client.get(f"/workspaces/{workspace['id']}/repositories", headers={"Authorization": f"Bearer {owner_token}"})
    assert listed.status_code == 200
    assert len(listed.json()) >= 1

    detail = client.get(f"/repositories/{repo_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert detail.status_code == 200
    assert detail.json()["name"] == "list-repo"


def test_update_and_delete_repository(client, db_session):
    owner = _create_user(db_session, email_suffix="repo-owner-update@example.com", full_name="Repository Owner Update")
    owner_token = _token_for(db_session, owner)
    workspace = _create_workspace(client, owner_token, name="Update Workspace", slug=f"update-ws-{uuid.uuid4().hex[:8]}")

    created = client.post(
        f"/workspaces/{workspace['id']}/repositories",
        json={
            "name": "update-repo",
            "provider": "GITHUB",
            "provider_repository_id": "4001",
            "clone_url": "https://github.com/test/update-repo.git",
            "default_branch": "develop",
            "visibility": "private",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 201
    repo_id = created.json()["id"]

    updated = client.patch(
        f"/repositories/{repo_id}",
        json={"name": "updated-repo", "default_branch": "main", "visibility": "public"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "updated-repo"

    deleted = client.delete(f"/repositories/{repo_id}", headers={"Authorization": f"Bearer {owner_token}"})
    assert deleted.status_code == 204


def test_developer_read_only_access(client, db_session):
    owner = _create_user(db_session, email_suffix="repo-owner-dev@example.com", full_name="Repository Owner Dev")
    developer = _create_user(db_session, email_suffix="repo-dev@example.com", full_name="Repository Developer")
    owner_token = _token_for(db_session, owner)
    developer_token = _token_for(db_session, developer)
    workspace = _create_workspace(client, owner_token, name="Dev Workspace", slug=f"dev-ws-{uuid.uuid4().hex[:8]}")
    _add_member(db_session, workspace["id"], developer.id, WorkspaceRole.DEVELOPER)

    created = client.post(
        f"/workspaces/{workspace['id']}/repositories",
        json={
            "name": "dev-repo",
            "provider": "GITHUB",
            "provider_repository_id": "5001",
            "clone_url": "https://github.com/test/dev-repo.git",
            "default_branch": "main",
            "visibility": "private",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 201
    repo_id = created.json()["id"]

    listed = client.get(f"/workspaces/{workspace['id']}/repositories", headers={"Authorization": f"Bearer {developer_token}"})
    assert listed.status_code == 200

    update_response = client.patch(
        f"/repositories/{repo_id}",
        json={"name": "nope"},
        headers={"Authorization": f"Bearer {developer_token}"},
    )
    assert update_response.status_code == 403

    delete_response = client.delete(f"/repositories/{repo_id}", headers={"Authorization": f"Bearer {developer_token}"})
    assert delete_response.status_code == 403


def test_repository_not_found_and_workspace_membership(client, db_session):
    owner = _create_user(db_session, email_suffix="repo-owner-missing@example.com", full_name="Repository Owner Missing")
    owner_token = _token_for(db_session, owner)

    missing = client.get("/repositories/00000000-0000-0000-0000-000000000000", headers={"Authorization": f"Bearer {owner_token}"})
    assert missing.status_code == 404

    other_user = _create_user(db_session, email_suffix="repo-other@example.com", full_name="Repository Other")
    other_token = _token_for(db_session, other_user)
    workspace = _create_workspace(client, owner_token, name="Membership Workspace", slug=f"member-ws-{uuid.uuid4().hex[:8]}")

    response = client.get(f"/workspaces/{workspace['id']}/repositories", headers={"Authorization": f"Bearer {other_token}"})
    assert response.status_code == 403


def test_jwt_protection(client):
    response = client.get("/repositories/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401
