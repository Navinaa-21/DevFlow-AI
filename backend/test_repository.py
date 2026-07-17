import time
import json
import urllib.request
import urllib.error
import subprocess
import sys
import uuid
from unittest.mock import patch

# Standard client request utility
def request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
        
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            if status == 204:
                return status, None
            body = response.read().decode("utf-8")
            return status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
            err_data = json.loads(err_body)
        except Exception:
            err_data = e.reason
        return e.code, err_data

def run_tests():
    from app.db.session import SessionLocal
    from app.models.user import User
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember
    from app.models.oauth_account import OAuthAccount
    from app.models.enums import AuthProvider, WorkspaceRole
    from app.services.auth_service import AuthService
    
    base_url = "http://127.0.0.1:8002"
    unique_id = uuid.uuid4().hex[:8]
    
    # 1. Setup Test Database Context
    db = SessionLocal()
    
    # Create two users (member and non-member)
    user_member = User(full_name="Member User", email=f"member.{unique_id}@example.com", is_active=True, is_verified=True)
    user_non_member = User(full_name="Non-Member User", email=f"nonmember.{unique_id}@example.com", is_active=True, is_verified=True)
    db.add_all([user_member, user_non_member])
    db.commit()
    db.refresh(user_member)
    db.refresh(user_non_member)
    
    # Create Workspace
    workspace = Workspace(name=f"Repo WS {unique_id}", slug=f"repo-ws-{unique_id}", is_active=True)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    
    # Add Member to Workspace
    member_link = WorkspaceMember(workspace_id=workspace.id, user_id=user_member.id, role=WorkspaceRole.DEVELOPER)
    db.add(member_link)
    
    # Create OAuthAccount for Member user
    oauth_acc = OAuthAccount(
        user_id=user_member.id,
        provider=AuthProvider.GITHUB,
        provider_user_id=f"github-id-{unique_id}",
        access_token="mock-github-access-token"
    )
    db.add(oauth_acc)
    db.commit()
    
    # Generate JWT Access Tokens
    auth_service = AuthService(db)
    member_token = auth_service.generate_auth_tokens(user_member)["access_token"]
    non_member_token = auth_service.generate_auth_tokens(user_non_member)["access_token"]
    
    db.close()
    
    headers_member = {"Authorization": f"Bearer {member_token}"}
    headers_non_member = {"Authorization": f"Bearer {non_member_token}"}
    
    print("\n--- Milestone 4: Repository Connection End-to-End Validation ---")
    
    try:
        # Test 1: Authentication Validation (No Token)
        print("\n1. Testing missing JWT token on protected endpoint...")
        status, res = request(f"{base_url}/workspaces/{workspace.id}/repositories", method="GET")
        assert status == 401, f"Expected 401, got {status} {res}"
        print("[OK] Missing token returns HTTP 401.")

        # Test 2: Authentication Validation (Invalid Token)
        print("\n2. Testing invalid JWT token on protected endpoint...")
        status, res = request(
            f"{base_url}/workspaces/{workspace.id}/repositories",
            method="GET",
            headers={"Authorization": "Bearer invalid-signature-token"}
        )
        assert status == 401, f"Expected 401, got {status}"
        print("[OK] Invalid token signature returns HTTP 401.")

        # Test 3: Workspace Authorization (Non-Member Access)
        print("\n3. Testing non-member access permissions (Workspace Member constraint)...")
        status, res = request(
            f"{base_url}/workspaces/{workspace.id}/repositories",
            method="GET",
            headers=headers_non_member
        )
        assert status == 403, f"Expected 403 Forbidden, got {status} {res}"
        assert "not a member" in res.get("detail", "").lower(), f"Unexpected error: {res}"
        print("[OK] Non-member request rejected with HTTP 403.")

        # Test 4: Workspace Presence Check (Non-existent Workspace)
        print("\n4. Testing non-existent workspace ID request...")
        bad_ws_uuid = str(uuid.uuid4())
        status, res = request(
            f"{base_url}/workspaces/{bad_ws_uuid}/repositories",
            method="GET",
            headers=headers_member
        )
        assert status == 404, f"Expected 404 Not Found, got {status} {res}"
        print("[OK] Non-existent workspace lookup rejected with HTTP 404.")

        # Test 5: Fetch External Repositories (Mocked GitHub Client)
        print("\n5. Listing external repositories from GitHub account...")
        status, repos = request(
            f"{base_url}/workspaces/{workspace.id}/repositories",
            method="GET",
            headers=headers_member
        )
        assert status == 200, f"Failed to list external repositories: {status} {repos}"
        assert len(repos) == 2, f"Expected 2 repositories, got {len(repos)}"
        assert repos[0]["name"] == "mock-repo-1"
        assert repos[0]["private"] is True
        print("[OK] External repositories listed successfully.")

        # Test 6: Connect a Repository
        print("\n6. Connecting repository 'mock-repo-1' to workspace...")
        connect_payload = {"repository_ids": ["123456"]}
        status, connected = request(
            f"{base_url}/workspaces/{workspace.id}/repositories/connect",
            method="POST",
            data=connect_payload,
            headers=headers_member
        )
        assert status == 201, f"Failed to connect repository: {status} {connected}"
        assert len(connected) == 1
        assert connected[0]["provider_repo_id"] == "123456"
        assert connected[0]["name"] == "mock-repo-1"
        repo_db_id = connected[0]["id"]
        print(f"[OK] Repository connected: DB ID {repo_db_id}")

        # Test 7: Verify Connected Listing
        print("\n7. Verifying connected repository appears in workspace listing...")
        status, connected_list = request(
            f"{base_url}/workspaces/{workspace.id}/repositories/connected",
            method="GET",
            headers=headers_member
        )
        assert status == 200
        assert len(connected_list) == 1
        assert connected_list[0]["provider_repo_id"] == "123456"
        assert connected_list[0]["is_active"] is True
        print("[OK] Connected listing returns active repository.")

        # Test 8: Attempt Duplicate Connection
        print("\n8. Attempting to connect duplicate repository (Integrity check)...")
        status, res = request(
            f"{base_url}/workspaces/{workspace.id}/repositories/connect",
            method="POST",
            data=connect_payload,
            headers=headers_member
        )
        assert status == 400, f"Expected 400, got {status} {res}"
        assert "already connected" in res.get("detail", "").lower(), f"Unexpected message: {res}"
        print("[OK] Duplicate connection request rejected with HTTP 400.")

        # Test 9: Deactivate Repository
        print("\n9. Deactivating connected repository...")
        status, _ = request(
            f"{base_url}/workspaces/{workspace.id}/repositories/{repo_db_id}",
            method="DELETE",
            headers=headers_member
        )
        assert status == 204, f"Failed to deactivate: {status}"
        
        # Verify it has is_active = False in connected listing
        status, connected_list = request(
            f"{base_url}/workspaces/{workspace.id}/repositories/connected",
            method="GET",
            headers=headers_member
        )
        assert status == 200
        assert len(connected_list) == 1
        assert connected_list[0]["is_active"] is False
        print("[OK] Deactivation completed successfully (is_active set to False).")

        # Test 10: Verify OpenAPI Documentation JSON
        print("\n10. Fetching OpenAPI spec to verify repository documentation...")
        status, openapi = request(f"{base_url}/openapi.json", method="GET")
        assert status == 200
        paths = openapi.get("paths", {})
        target_path = "/workspaces/{workspace_id}/repositories"
        assert target_path in paths, "Repositories paths missing from OpenAPI specs"
        assert "post" in paths[target_path + "/connect"], "Connect path post mapping missing"
        print("[OK] OpenAPI metadata verified.")

    finally:
        # Clean up database records
        db = SessionLocal()
        db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace.id).delete()
        db.query(OAuthAccount).filter(OAuthAccount.user_id == user_member.id).delete()
        db.query(Workspace).filter(Workspace.id == workspace.id).delete()
        db.query(User).filter(User.id.in_([user_member.id, user_non_member.id])).delete()
        db.commit()
        db.close()
        print("\nClean up of test databases completed.")

if __name__ == "__main__":
    # Start the local server
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8002", "--host", "127.0.0.1"],
        cwd="."
    )
    
    # We patch GitHubClient.get_repositories globally inside the test execution context
    mock_repos = [
        {
            "id": 123456,
            "name": "mock-repo-1",
            "full_name": "test-user/mock-repo-1",
            "html_url": "https://github.com/test-user/mock-repo-1",
            "default_branch": "main",
            "private": True,
            "description": "First mock repository"
        },
        {
            "id": 789012,
            "name": "mock-repo-2",
            "full_name": "test-user/mock-repo-2",
            "html_url": "https://github.com/test-user/mock-repo-2",
            "default_branch": "main",
            "private": False,
            "description": "Second mock repository"
        }
    ]
    
    # Patch the Async GitHub client method
    async def mock_get_repos(self):
        return mock_repos

    patcher = patch("app.utils.github_client.GitHubClient.get_repositories", mock_get_repos)
    patcher.start()
    
    try:
        print("Starting uvicorn server...")
        time.sleep(2)
        
        run_tests()
        print("\nALL REPOSITORY CONNECTION lifecycle TESTS PASSED SUCCESSFULLY!")
    except Exception as e:
        print(f"\nValidation Test Failed: {e}")
        sys.exit(1)
    finally:
        patcher.stop()
        print("Shutting down uvicorn server...")
        server_process.terminate()
        server_process.wait()
