import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.db.database import engine
from app.db.session import SessionLocal, get_db
from app.main import app
from app.models.base import Base
from app.models.enums import InvitationStatus, WorkspaceRole
from app.models.invitation import Invitation
from app.models.user import User
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


def _create_user(db_session, email, full_name):
    user = User(full_name=full_name, email=email, is_active=True, is_verified=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _auth_token(db_session, user):
    return AuthService(db_session).generate_auth_tokens(user)["access_token"]


def test_accept_invitation_successfully(db_session):
    service = WorkspaceService(db_session)
    owner = _create_user(db_session, f"owner-{uuid.uuid4().hex[:8]}@example.com", "Owner")
    invitee = _create_user(db_session, f"invitee-{uuid.uuid4().hex[:8]}@example.com", "Invitee")

    workspace = service.create_workspace(owner, WorkspaceCreateRequest(name="Invite Workspace", slug=f"invite-{uuid.uuid4().hex[:8]}"))
    invitation = service.invite_member(owner, workspace.id, invitee.email, WorkspaceRole.DEVELOPER)

    accepted = service.accept_invitation(invitation.token, invitee)

    assert accepted.status == InvitationStatus.ACCEPTED
    assert service.repository.get_member(workspace.id, invitee.id) is not None


def test_decline_invitation_successfully(db_session):
    service = WorkspaceService(db_session)
    owner = _create_user(db_session, f"owner2-{uuid.uuid4().hex[:8]}@example.com", "Owner2")
    invitee = _create_user(db_session, f"invitee2-{uuid.uuid4().hex[:8]}@example.com", "Invitee2")

    workspace = service.create_workspace(owner, WorkspaceCreateRequest(name="Decline Workspace", slug=f"decline-{uuid.uuid4().hex[:8]}"))
    invitation = service.invite_member(owner, workspace.id, invitee.email, WorkspaceRole.DEVELOPER)

    declined = service.decline_invitation(invitation.token, invitee)

    assert declined.status == InvitationStatus.DECLINED


def test_expired_invitation(db_session):
    service = WorkspaceService(db_session)
    owner = _create_user(db_session, f"owner3-{uuid.uuid4().hex[:8]}@example.com", "Owner3")
    invitee = _create_user(db_session, f"invitee3-{uuid.uuid4().hex[:8]}@example.com", "Invitee3")

    workspace = service.create_workspace(owner, WorkspaceCreateRequest(name="Expired Workspace", slug=f"expired-{uuid.uuid4().hex[:8]}"))
    invitation = service.repository.create_invitation(
        workspace_id=workspace.id,
        email=invitee.email,
        role=WorkspaceRole.DEVELOPER,
        token="expired-token",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        inviter_id=owner.id
    )

    with pytest.raises(Exception):
        service.accept_invitation(invitation.token, invitee)

    refreshed = service.repository.get_invitation(invitation.id)
    assert refreshed.status == InvitationStatus.EXPIRED


def test_invalid_token_and_email_mismatch(db_session):
    service = WorkspaceService(db_session)
    owner = _create_user(db_session, f"owner4-{uuid.uuid4().hex[:8]}@example.com", "Owner4")
    invitee = _create_user(db_session, f"invitee4-{uuid.uuid4().hex[:8]}@example.com", "Invitee4")
    other_user = _create_user(db_session, f"other4-{uuid.uuid4().hex[:8]}@example.com", "Other4")

    workspace = service.create_workspace(owner, WorkspaceCreateRequest(name="Mismatch Workspace", slug=f"mismatch-{uuid.uuid4().hex[:8]}"))
    invitation = service.invite_member(owner, workspace.id, invitee.email, WorkspaceRole.DEVELOPER)

    with pytest.raises(Exception):
        service.accept_invitation("does-not-exist", invitee)

    with pytest.raises(Exception):
        service.accept_invitation(invitation.token, other_user)


def test_duplicate_workspace_member_rejected(db_session):
    service = WorkspaceService(db_session)
    owner = _create_user(db_session, f"owner5-{uuid.uuid4().hex[:8]}@example.com", "Owner5")
    invitee = _create_user(db_session, f"invitee5-{uuid.uuid4().hex[:8]}@example.com", "Invitee5")

    workspace = service.create_workspace(owner, WorkspaceCreateRequest(name="Duplicate Workspace", slug=f"duplicate-{uuid.uuid4().hex[:8]}"))
    service.repository.add_member(workspace.id, invitee.id, WorkspaceRole.DEVELOPER)

    with pytest.raises(Exception):
        service.invite_member(owner, workspace.id, invitee.email, WorkspaceRole.DEVELOPER)


def test_cancel_and_resend_invitation(db_session):
    service = WorkspaceService(db_session)
    owner = _create_user(db_session, f"owner6-{uuid.uuid4().hex[:8]}@example.com", "Owner6")
    invitee = _create_user(db_session, f"invitee6-{uuid.uuid4().hex[:8]}@example.com", "Invitee6")

    workspace = service.create_workspace(owner, WorkspaceCreateRequest(name="Lifecycle Workspace", slug=f"lifecycle-{uuid.uuid4().hex[:8]}"))
    invitation = service.invite_member(owner, workspace.id, invitee.email, WorkspaceRole.DEVELOPER)

    cancelled = service.cancel_invitation(workspace.id, invitation.id, owner)
    assert cancelled.status == InvitationStatus.CANCELLED

    invitation = service.repository.create_invitation(
        workspace_id=workspace.id,
        email=invitee.email,
        role=WorkspaceRole.DEVELOPER,
        token="resend-token",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        inviter_id=owner.id
    )
    resent = service.resend_invitation(workspace.id, invitation.id, owner)
    assert resent.status == InvitationStatus.PENDING
    assert resent.expires_at > datetime.now(timezone.utc) + timedelta(days=1) - timedelta(seconds=5)


def test_already_accepted_invitation_rejected(db_session):
    service = WorkspaceService(db_session)
    owner = _create_user(db_session, f"owner7-{uuid.uuid4().hex[:8]}@example.com", "Owner7")
    invitee = _create_user(db_session, f"invitee7-{uuid.uuid4().hex[:8]}@example.com", "Invitee7")

    workspace = service.create_workspace(owner, WorkspaceCreateRequest(name="Accepted Workspace", slug=f"accepted-{uuid.uuid4().hex[:8]}"))
    invitation = service.invite_member(owner, workspace.id, invitee.email, WorkspaceRole.DEVELOPER)
    service.accept_invitation(invitation.token, invitee)

    with pytest.raises(Exception):
        service.accept_invitation(invitation.token, invitee)


def test_jwt_protection_and_forbidden_actions(client, db_session):
    service = WorkspaceService(db_session)
    owner = _create_user(db_session, f"owner8-{uuid.uuid4().hex[:8]}@example.com", "Owner8")
    developer = _create_user(db_session, f"developer8-{uuid.uuid4().hex[:8]}@example.com", "Developer8")
    invitee = _create_user(db_session, f"invitee8-{uuid.uuid4().hex[:8]}@example.com", "Invitee8")

    workspace = service.create_workspace(owner, WorkspaceCreateRequest(name="API Workspace", slug=f"api-{uuid.uuid4().hex[:8]}"))
    service.repository.add_member(workspace.id, developer.id, WorkspaceRole.DEVELOPER)
    invitation = service.invite_member(owner, workspace.id, invitee.email, WorkspaceRole.DEVELOPER)

    unauthorized = client.post(f"/invitations/{invitation.token}/accept")
    assert unauthorized.status_code == 401

    developer_token = _auth_token(db_session, developer)
    forbidden = client.post(
        f"/workspaces/{workspace.id}/invitations/{invitation.id}/cancel",
        headers={"Authorization": f"Bearer {developer_token}"},
    )
    assert forbidden.status_code == 403

    owner_token = _auth_token(db_session, owner)
    cancelled = client.post(
        f"/workspaces/{workspace.id}/invitations/{invitation.id}/cancel",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert cancelled.status_code == 200
