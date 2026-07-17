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
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreateRequest
from app.services.auth_service import AuthService
from app.services.workspace_service import WorkspaceService


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


def test_repository_create_and_list_members(db_session):
    repo = WorkspaceRepository(db_session)
    owner = _create_user(db_session, email_suffix="owner-repo@example.com", full_name="Owner Repo")
    payload = WorkspaceCreateRequest(name="Repo Workspace", slug=f"repo-{uuid.uuid4().hex[:8]}", description="Repo workspace")
    workspace = repo.create_workspace(payload)

    created_member = repo.add_member(workspace.id, owner.id, WorkspaceRole.OWNER)
    assert created_member.role == WorkspaceRole.OWNER

    member = repo.get_member(workspace.id, owner.id)
    assert member is not None

    members = repo.list_members(workspace.id)
    assert len(members) == 1

    workspaces = repo.list_user_workspaces(owner.id)
    assert any(ws.id == workspace.id for ws in workspaces)

    removed = repo.remove_member(workspace.id, owner.id)
    assert removed is True
    assert repo.get_member(workspace.id, owner.id) is None


def test_service_rules_for_workspace_membership(db_session):
    service = WorkspaceService(db_session)
    owner = _create_user(db_session, email_suffix="owner-service@example.com", full_name="Owner Service")
    invitee = _create_user(db_session, email_suffix="invitee@example.com", full_name="Invitee")

    workspace = service.create_workspace(owner, WorkspaceCreateRequest(name="Service Workspace", slug=f"service-{uuid.uuid4().hex[:8]}", description="Service workspace"))
    assert workspace.id is not None

    with pytest.raises(Exception):
        service.create_workspace(owner, WorkspaceCreateRequest(name="Duplicate", slug=workspace.slug, description="Dup"))

    developer = _create_user(db_session, email_suffix="developer@example.com", full_name="Developer")
    service.repository.add_member(workspace.id, developer.id, WorkspaceRole.DEVELOPER)
    with pytest.raises(Exception):
        service.invite_member(developer, workspace.id, invitee.email, WorkspaceRole.DEVELOPER)

    service.invite_member(owner, workspace.id, invitee.email, WorkspaceRole.DEVELOPER)

    with pytest.raises(Exception):
        service.invite_member(owner, workspace.id, invitee.email, WorkspaceRole.DEVELOPER)

    with pytest.raises(Exception):
        service.remove_member(owner, workspace.id, owner.id)


def test_workspace_api_protection_and_membership(client, db_session):
    owner = _create_user(db_session, email_suffix="owner-api@example.com", full_name="Owner API")
    other_user = _create_user(db_session, email_suffix="other-api@example.com", full_name="Other User")
    owner_token = _token_for(db_session, owner)
    other_token = _token_for(db_session, other_user)

    response = client.post(
        "/workspaces",
        json={"name": "API Workspace", "slug": f"api-{uuid.uuid4().hex[:8]}", "description": "API workspace"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 201
    workspace_id = response.json()["id"]

    unauthenticated = client.get("/workspaces")
    assert unauthenticated.status_code == 401

    listed = client.get("/workspaces", headers={"Authorization": f"Bearer {owner_token}"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    forbidden = client.get(f"/workspaces/{workspace_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert forbidden.status_code == 403

    invite_response = client.post(
        f"/workspaces/{workspace_id}/invitations",
        json={"email": other_user.email, "role": "DEVELOPER"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert invite_response.status_code == 201

    remove_response = client.delete(
        f"/workspaces/{workspace_id}/members/{other_user.id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert remove_response.status_code == 200
