import urllib.request
import urllib.error
import json
import uuid

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

def run_demo():
    from app.db.session import SessionLocal
    from app.models.user import User
    from app.models.oauth_account import OAuthAccount
    from app.models.enums import AuthProvider, WorkspaceRole
    from app.services.auth_service import AuthService
    
    base_url = "http://127.0.0.1:8000"
    
    # 1. Provision Demo User in PostgreSQL
    db = SessionLocal()
    demo_email = f"user.{uuid.uuid4().hex[:8]}@example.com"
    demo_user = User(
        full_name="Demo User",
        email=demo_email,
        is_active=True,
        is_verified=True
    )
    db.add(demo_user)
    db.commit()
    db.refresh(demo_user)
    
    # Link mock GitHub account
    oauth_acc = OAuthAccount(
        user_id=demo_user.id,
        provider=AuthProvider.GITHUB,
        provider_user_id=f"github-{uuid.uuid4().hex[:8]}",
        access_token="mock-github-access-token"
    )
    db.add(oauth_acc)
    db.commit()
    
    # Generate session tokens
    auth_service = AuthService(db)
    tokens = auth_service.generate_auth_tokens(demo_user)
    access_token = tokens["access_token"]
    db.close()
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    print("==============================================================")
    print("PHASE 1 INTEGRATION FLOW: COMPLETE USER LIFECYCLE SIMULATION")
    print("==============================================================")
    print(f"Logged in as User: {demo_user.full_name} ({demo_user.email})")
    
    # 2. Create Workspace
    suffix = uuid.uuid4().hex[:6]
    ws_name = f"Vanguard Engineering {suffix}"
    ws_slug = f"vanguard-engineering-{suffix}"
    print(f"\n[Action 1] Creating workspace: '{ws_name}'...")
    ws_payload = {
        "name": ws_name,
        "slug": ws_slug,
        "owner_id": str(demo_user.id),
        "description": "Primary workspace for engineering collaboration"
    }
    status, ws = request(f"{base_url}/workspaces", method="POST", data=ws_payload, headers=headers)
    if status != 201:
        print(f"Failed to create workspace: {status} {ws}")
        return
    ws_id = ws["id"]
    print(f"[Success] Workspace provisioned successfully! ID: {ws_id} | Slug: {ws['slug']}")
    
    # 3. Retrieve External Repositories
    print("\n[Action 2] Fetching available GitHub repositories...")
    status, external_repos = request(f"{base_url}/workspaces/{ws_id}/repositories", method="GET", headers=headers)
    if status != 200:
        print(f"Failed to fetch external repositories: {status} {external_repos}")
        return
    print(f"[Success] Discovered {len(external_repos)} repositories on user's GitHub account:")
    for repo in external_repos:
        print(f"  - Name: {repo['name']} | Path: {repo['full_name']} | Default Branch: {repo['default_branch']}")
        
    # 4. Connect Selected Repositories
    print("\n[Action 3] Connecting selected GitHub repositories to workspace...")
    connect_payload = {"repository_ids": ["123456", "789012"]}
    status, connected = request(f"{base_url}/workspaces/{ws_id}/repositories/connect", method="POST", data=connect_payload, headers=headers)
    if status != 201:
        print(f"Failed to connect repositories: {status} {connected}")
        return
    print(f"[Success] Connected {len(connected)} repositories to workspace:")
    for r in connected:
         print(f"  - DB ID: {r['id']} | Path: {r['full_name']} | Active status: {r['is_active']}")
         
    # 5. Send Team Invitation
    print("\n[Action 4] Inviting new team member 'colleague@example.com' as Developer...")
    invite_payload = {
        "email": "colleague@example.com",
        "role": "DEVELOPER"
    }
    status, invite = request(f"{base_url}/workspaces/{ws_id}/invitations", method="POST", data=invite_payload, headers=headers)
    if status != 201:
        print(f"Failed to send invitation: {status} {invite}")
        return
    print(f"[Success] Invitation sent! Status: {invite['status']} | Expires: {invite['expires_at']}")
    
    # 6. Fetch Dashboard Aggregates
    print("\n[Action 5] Aggregating dashboard overview...")
    # Fetch connected list
    status, repos_list = request(f"{base_url}/workspaces/{ws_id}/repositories/connected", method="GET", headers=headers)
    # Fetch members list
    status, members_list = request(f"{base_url}/workspaces/{ws_id}/members", method="GET", headers=headers)
    # Fetch invitations list
    status, invites_list = request(f"{base_url}/workspaces/{ws_id}/invitations", method="GET", headers=headers)
    
    print("\n==============================================================")
    print("DASHBOARD SUMMARIZED OUTPUT")
    print("==============================================================")
    print(f"Workspace Name: {ws['name']}")
    print(f"Workspace Slug: {ws['slug']}")
    print(f"Total Connected Repositories: {len(repos_list)}")
    for r in repos_list:
        print(f"  * {r['full_name']} ({r['provider']}) - Status: {'Active' if r['is_active'] else 'Inactive'}")
    print(f"Workspace Members Count: {len(members_list)}")
    for m in members_list:
        print(f"  * {m['full_name']} ({m['email']}) - Role: {m['role']}")
    print(f"Pending Invitations: {len([i for i in invites_list if i['status'] == 'PENDING'])}")
    for i in invites_list:
        if i['status'] == 'PENDING':
            print(f"  * {i['email']} - Invited Role: {i['role']}")
    print("==============================================================")

if __name__ == "__main__":
    run_demo()
