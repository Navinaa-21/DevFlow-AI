import time
import json
import urllib.request
import urllib.error
import subprocess
import sys
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

def run_tests():
    base_url = "http://127.0.0.1:8002"
    unique_id = uuid.uuid4().hex[:8]
    
    # 0. Test health endpoints
    print("0a. Testing GET /health...")
    status, health = request(f"{base_url}/health", method="GET")
    assert status == 200, f"Health check failed: {status}"
    
    # 1. Create Owner User
    print("\n1. Creating owner user...")
    user_payload = {
        "full_name": "Workspace Owner",
        "email": f"owner.{unique_id}@example.com",
        "avatar_url": "https://example.com/owner.png",
        "is_verified": True,
        "is_active": True
    }
    status, user = request(f"{base_url}/users/", method="POST", data=user_payload)
    assert status == 201
    owner_id = user["id"]
    print(f"[OK] User created successfully: ID {owner_id}")

    # 2. Successful Workspace Creation
    print("\n2. Creating workspace...")
    ws_payload = {
        "name": f"Workspace {unique_id}",
        "slug": f"workspace-{unique_id}",
        "description": "Valid workspace description",
        "logo_url": "https://example.com/logo.png",
        "is_active": True,
        "owner_id": owner_id
    }
    status, workspace = request(f"{base_url}/workspaces", method="POST", data=ws_payload)
    assert status == 201, f"Failed to create workspace: {status} {workspace}"
    workspace_id = workspace["id"]
    print(f"[OK] Workspace created: ID {workspace_id}")

    # 3. Test Validation: Invalid UUID path parameter
    print("\n3. Testing invalid UUID format on GET /workspaces/{workspace_id}...")
    status, err = request(f"{base_url}/workspaces/not-a-valid-uuid", method="GET")
    assert status == 422, f"Expected 422 Unprocessable Entity, got {status} {err}"
    print("[OK] Invalid UUID path format rejected with 422.")

    # 4. Test Validation: Missing Workspace
    print("\n4. Testing missing workspace GET (valid UUID format)...")
    random_uuid = str(uuid.uuid4())
    status, err = request(f"{base_url}/workspaces/{random_uuid}", method="GET")
    assert status == 404, f"Expected 404, got {status} {err}"
    assert "Workspace not found" in err.get("detail", ""), f"Unexpected error detail: {err}"
    print("[OK] Missing workspace returned 404.")

    # 5. Test Business Rule Validation: Duplicate Workspace Name
    print("\n5. Testing duplicate workspace name restriction...")
    duplicate_name_payload = {
        "name": f"Workspace {unique_id}",  # Same name
        "slug": f"workspace-diff-{unique_id}",
        "description": "Different slug, same name",
        "logo_url": "https://example.com/logo.png",
        "is_active": True,
        "owner_id": owner_id
    }
    status, err = request(f"{base_url}/workspaces", method="POST", data=duplicate_name_payload)
    assert status == 400, f"Expected 400 Bad Request, got {status} {err}"
    assert "name already exists" in err.get("detail", "").lower(), f"Unexpected error detail: {err}"
    print("[OK] Duplicate workspace name rejected with 400.")

    # 6. Test Business Rule Validation: Duplicate Workspace Slug
    print("\n6. Testing duplicate workspace slug restriction...")
    duplicate_slug_payload = {
        "name": f"Workspace Different {unique_id}",
        "slug": f"workspace-{unique_id}",  # Same slug
        "description": "Different name, same slug",
        "logo_url": "https://example.com/logo.png",
        "is_active": True,
        "owner_id": owner_id
    }
    status, err = request(f"{base_url}/workspaces", method="POST", data=duplicate_slug_payload)
    assert status == 400, f"Expected 400 Bad Request, got {status} {err}"
    assert "slug already exists" in err.get("detail", "").lower(), f"Unexpected error detail: {err}"
    print("[OK] Duplicate workspace slug rejected with 400.")

    # 7. Test Validation: Invalid Request Payload (Slug Format / Uppercase / Spaces)
    print("\n7. Testing invalid payload (slug containing uppercase and spaces)...")
    bad_payload = {
        "name": "Another Workspace",
        "slug": "Workspace Bad Format",  # Spaces and uppercase are prohibited by our SLUG_REGEX
        "description": "Valid description",
        "logo_url": "https://example.com/logo.png",
        "is_active": True,
        "owner_id": owner_id
    }
    status, err = request(f"{base_url}/workspaces", method="POST", data=bad_payload)
    assert status == 422, f"Expected 422 Unprocessable Entity, got {status} {err}"
    print("[OK] Invalid slug regex rejected with 422.")

    # 8. Test Validation: Invalid logo_url format
    print("\n8. Testing invalid logo_url format...")
    bad_url_payload = {
        "name": f"Workspace New {unique_id}",
        "slug": f"workspace-new-{unique_id}",
        "description": "Valid description",
        "logo_url": "not-a-valid-url-format",  # Prohibited by TypeAdapter(HttpUrl)
        "is_active": True,
        "owner_id": owner_id
    }
    status, err = request(f"{base_url}/workspaces", method="POST", data=bad_url_payload)
    assert status == 422, f"Expected 422, got {status} {err}"
    print("[OK] Invalid URL format rejected with 422.")

    # 9. Test Pagination, Search, Sorting, Filtering
    print("\n9. Testing pagination, searching, sorting, and filtering on GET /workspaces...")
    # Add a second workspace to test sorting / searching
    second_ws_payload = {
        "name": f"Alpha Workspace {unique_id}",
        "slug": f"alpha-ws-{unique_id}",
        "description": "Contains alpha search keyword",
        "logo_url": "https://example.com/logo.png",
        "is_active": True,
        "owner_id": owner_id
    }
    status, second_ws = request(f"{base_url}/workspaces", method="POST", data=second_ws_payload)
    assert status == 201
    second_ws_id = second_ws["id"]

    # 9a. Test Search
    status, search_res = request(f"{base_url}/workspaces?search=alpha", method="GET")
    assert status == 200
    assert "items" in search_res
    assert any(ws["id"] == second_ws_id for ws in search_res["items"]), "Search should return alpha workspace"
    assert not any(ws["id"] == workspace_id for ws in search_res["items"]), "Search should filter out first workspace"

    # 9b. Test Sorting (sort_by = -name)
    status, sort_res = request(f"{base_url}/workspaces?sort_by=-name", method="GET")
    assert status == 200
    items = sort_res["items"]
    # Verify both workspaces are in items, and f"Workspace {unique_id}" comes before f"Alpha Workspace {unique_id}" on descending sort
    ids = [ws["id"] for ws in items]
    assert ids.index(workspace_id) < ids.index(second_ws_id), "Sorting descending by name failed"

    # 9c. Test Pagination metadata
    status, pag_res = request(f"{base_url}/workspaces?limit=1&skip=0", method="GET")
    assert status == 200
    assert pag_res["limit"] == 1
    assert pag_res["offset"] == 0
    assert pag_res["total"] >= 2
    assert len(pag_res["items"]) == 1
    print("[OK] Listing parameters (search, sorting, pagination metadata) verified.")

    # 10. PATCH Workspace
    print(f"\n10. Testing partial update PATCH /workspaces/{workspace_id}...")
    patch_payload = {
        "name": f"Updated Workspace {unique_id}",
        "description": "Partially updated description"
    }
    status, patched_ws = request(f"{base_url}/workspaces/{workspace_id}", method="PATCH", data=patch_payload)
    assert status == 200
    assert patched_ws["name"] == f"Updated Workspace {unique_id}"
    assert patched_ws["description"] == "Partially updated description"
    print("[OK] PATCH workspace successfully executed.")

    # 11. DELETE Workspace & verify clean state
    print(f"\n11. Testing DELETE /workspaces/{workspace_id} and DELETE /workspaces/{second_ws_id}...")
    status, _ = request(f"{base_url}/workspaces/{workspace_id}", method="DELETE")
    assert status == 204
    status, _ = request(f"{base_url}/workspaces/{second_ws_id}", method="DELETE")
    assert status == 204

    # Verify 404
    status, _ = request(f"{base_url}/workspaces/{workspace_id}", method="GET")
    assert status == 404
    print("[OK] Workspaces deleted and confirmed clean.")

    # Clean up Owner User
    status, _ = request(f"{base_url}/users/{owner_id}", method="DELETE")
    assert status == 204
    print("[OK] Owner user cleaned up.")

if __name__ == "__main__":
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8002", "--host", "127.0.0.1"],
        cwd="."
    )
    
    try:
        print("Starting uvicorn server...")
        time.sleep(2)
        
        run_tests()
        print("\nALL END-TO-END VALIDATION TESTS PASSED SUCCESSFULLY!")
    except Exception as e:
        print(f"\n❌ Validation Test Failed: {e}")
        sys.exit(1)
    finally:
        print("Shutting down uvicorn server...")
        server_process.terminate()
        server_process.wait()
