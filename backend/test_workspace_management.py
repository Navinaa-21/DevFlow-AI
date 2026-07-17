import uuid

import pytest
from fastapi.testclient import TestClient

from app.db.database import engine
from app.db.session import SessionLocal, get_db
from app.main import app
from app.models.base import Base
from app.models.enums import InvitationStatus, WorkspaceRole
from app.models.invitation import Invitation
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
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


def test_update_workspace_successfully(client, db_session):
    owner = _create_user(db_session, email_suffix="owner-update@example.com", full_name="Owner Update")
    owner_token = _token_for(db_session, owner)

    workspace = client.post(
        "/workspaces",
        json={"name": "Update Workspace", "slug": f"update-{uuid.uuid4().hex[:8]}", "description": "Original"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]

    response = client.patch(
        f"/workspaces/{workspace_id}",
        json={"name": "Updated Workspace", "description": "Updated", "slug": f"updated-{uuid.uuid4().hex[:8]}"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Updated Workspace"
    assert payload["description"] == "Updated"


def test_duplicate_slug_rejected(client, db_session):
    owner = _create_user(db_session, email_suffix="owner-dup@example.com", full_name="Owner Dup")
    owner_token = _token_for(db_session, owner)

    first = client.post(
        "/workspaces",
        json={"name": "First Workspace", "slug": f"dup-{uuid.uuid4().hex[:8]}", "description": "First"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    second = client.post(
        "/workspaces",
        json={"name": "Second Workspace", "slug": f"dup2-{uuid.uuid4().hex[:8]}", "description": "Second"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert first.status_code == 201
    assert second.status_code == 201

    response = client.patch(
        f"/workspaces/{second.json()['id']}",
        json={"slug": first.json()["slug"]},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 400


def test_unauthorized_update(client, db_session):
    owner = _create_user(db_session, email_suffix="owner-unauth@example.com", full_name="Owner Unauth")
    owner_token = _token_for(db_session, owner)

    workspace = client.post(
        "/workspaces",
        json={"name": "Private Workspace", "slug": f"private-{uuid.uuid4().hex[:8]}", "description": "Private"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert workspace.status_code == 201

    response = client.patch(
        f"/workspaces/{workspace.json()['id']}",
        json={"name": "New Name"},
    )

    assert response.status_code == 401


def test_delete_workspace_successfully(client, db_session):
    owner = _create_user(db_session, email_suffix="owner-delete@example.com", full_name="Owner Delete")
    owner_token = _token_for(db_session, owner)

    workspace = client.post(
        "/workspaces",
        json={"name": "Delete Workspace", "slug": f"delete-{uuid.uuid4().hex[:8]}", "description": "Delete me"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert workspace.status_code == 201

    response = client.delete(
        f"/workspaces/{workspace.json()['id']}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 204


def test_manager_delete_forbidden(client, db_session):
    owner = _create_user(db_session, email_suffix="owner-manager-delete@example.com", full_name="Owner Manager")
    manager = _create_user(db_session, email_suffix="manager-delete@example.com", full_name="Manager Delete")
    owner_token = _token_for(db_session, owner)
    manager_token = _token_for(db_session, manager)

    workspace = client.post(
        "/workspaces",
        json={"name": "Manager Delete Workspace", "slug": f"manager-delete-{uuid.uuid4().hex[:8]}", "description": "Manager delete"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]

    service = WorkspaceService(db_session)
    service.repository.add_member(workspace_id, manager.id, WorkspaceRole.MANAGER)

    response = client.delete(
        f"/workspaces/{workspace_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )

    assert response.status_code == 403


def test_developer_delete_forbidden(client, db_session):
    owner = _create_user(db_session, email_suffix="owner-dev-delete@example.com", full_name="Owner Dev")
    developer = _create_user(db_session, email_suffix="dev-delete@example.com", full_name="Developer Delete")
    owner_token = _token_for(db_session, owner)
    developer_token = _token_for(db_session, developer)

    workspace = client.post(
        "/workspaces",
        json={"name": "Developer Delete Workspace", "slug": f"dev-delete-{uuid.uuid4().hex[:8]}", "description": "Developer delete"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]

    service = WorkspaceService(db_session)
    service.repository.add_member(workspace_id, developer.id, WorkspaceRole.DEVELOPER)

    response = client.delete(
        f"/workspaces/{workspace_id}",
        headers={"Authorization": f"Bearer {developer_token}"},
    )

    assert response.status_code == 403


def test_transfer_ownership_successfully(client, db_session):
    owner = _create_user(db_session, email_suffix="owner-transfer@example.com", full_name="Owner Transfer")
    manager = _create_user(db_session, email_suffix="manager-transfer@example.com", full_name="Manager Transfer")
    owner_token = _token_for(db_session, owner)

    workspace = client.post(
        "/workspaces",
        json={"name": "Transfer Workspace", "slug": f"transfer-{uuid.uuid4().hex[:8]}", "description": "Transfer"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]

    service = WorkspaceService(db_session)
    service.repository.add_member(workspace_id, manager.id, WorkspaceRole.MANAGER)

    response = client.post(
        f"/workspaces/{workspace_id}/transfer-ownership",
        json={"new_owner_id": str(manager.id)},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 200


def test_transfer_ownership_to_non_member(client, db_session):
    owner = _create_user(db_session, email_suffix="owner-nonmember@example.com", full_name="Owner Nonmember")
    non_member = _create_user(db_session, email_suffix="nonmember@example.com", full_name="Non Member")
    owner_token = _token_for(db_session, owner)

    workspace = client.post(
        "/workspaces",
        json={"name": "Nonmember Workspace", "slug": f"nonmember-{uuid.uuid4().hex[:8]}", "description": "Nonmember"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert workspace.status_code == 201

    response = client.post(
        f"/workspaces/{workspace.json()['id']}/transfer-ownership",
        json={"new_owner_id": str(non_member.id)},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 409


def test_workspace_not_found(client, db_session):
    owner = _create_user(db_session, email_suffix="owner-notfound@example.com", full_name="Owner Notfound")
    owner_token = _token_for(db_session, owner)

    response = client.patch(
        "/workspaces/00000000-0000-0000-0000-000000000000",
        json={"name": "Ghost"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 404


def test_developer_cannot_update_workspace(client, db_session):
    owner = _create_user(db_session, email_suffix="owner-dev-update@example.com", full_name="Owner Dev Update")
    developer = _create_user(db_session, email_suffix="developer-update@example.com", full_name="Developer Update")
    owner_token = _token_for(db_session, owner)
    developer_token = _token_for(db_session, developer)

    workspace = client.post(
        "/workspaces",
        json={"name": "Developer Update Workspace", "slug": f"dev-update-{uuid.uuid4().hex[:8]}", "description": "Update me"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]

    service = WorkspaceService(db_session)
    service.repository.add_member(workspace_id, developer.id, WorkspaceRole.DEVELOPER)

    response = client.patch(
        f"/workspaces/{workspace_id}",
        json={"name": "Nope"},
        headers={"Authorization": f"Bearer {developer_token}"},
    )

    assert response.status_code == 403


def test_cascade_delete_removes_members_and_invitations(client, db_session):
    owner = _create_user(db_session, email_suffix="owner-cascade@example.com", full_name="Owner Cascade")
    invitee = _create_user(db_session, email_suffix="invitee-cascade@example.com", full_name="Invitee Cascade")
    owner_token = _token_for(db_session, owner)

    workspace = client.post(
        "/workspaces",
        json={"name": "Cascade Workspace", "slug": f"cascade-{uuid.uuid4().hex[:8]}", "description": "Cascade"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]

    invite = client.post(
        f"/workspaces/{workspace_id}/invitations",
        json={"email": invitee.email, "role": "DEVELOPER"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert invite.status_code == 201

    response = client.delete(
        f"/workspaces/{workspace_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 204

    remaining_members = db_session.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).count()
    remaining_invitations = db_session.query(Invitation).filter(Invitation.workspace_id == workspace_id).count()
    assert remaining_members == 0
    assert remaining_invitations == 0


def test_existing_authentication_flow_still_works(client, db_session):
    response = client.post(
        "/auth/register",
        json={"full_name": "Auth Flow", "email": f"auth-flow-{uuid.uuid4().hex[:8]}@example.com", "password": "testpass123"},
    )

    assert response.status_code in {200, 201}
    assert "access_token" in response.json()
