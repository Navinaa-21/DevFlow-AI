import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    unique_id = str(uuid.uuid4())[:8]
    test_email = f"api_{unique_id}@example.com"
    test_password = "SecurePassword123!"
    
    print("Running Authentication API tests...")
    
    # 1. Register User
    res = client.post("/auth/register", json={
        "full_name": "API Test User",
        "email": test_email,
        "password": test_password
    })
    assert res.status_code == 201, f"Failed to register: {res.text}"
    tokens = res.json()
    assert "access_token" in tokens, "Missing access_token"
    print("? POST /auth/register returns 201 and JWT payload")
    
    # 2. Register duplicate
    res = client.post("/auth/register", json={
        "full_name": "Duplicate User",
        "email": test_email,
        "password": test_password
    })
    assert res.status_code == 409, f"Should return 409 Conflict for duplicate: {res.text}"
    print("? POST /auth/register returns 409 Conflict for duplicate email")
    
    # 3. Login
    res = client.post("/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    assert res.status_code == 200, f"Failed to login: {res.text}"
    login_tokens = res.json()
    assert "access_token" in login_tokens, "Missing access_token on login"
    print("? POST /auth/login returns 200 and JWT payload")
    
    # 4. Login wrong password
    res = client.post("/auth/login", json={
        "email": test_email,
        "password": "WrongPassword!"
    })
    assert res.status_code == 401, f"Should return 401 for wrong password: {res.text}"
    print("? POST /auth/login returns 401 Unauthorized for wrong credentials")
    
    # 5. Get current user
    access_token = login_tokens["access_token"]
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert res.status_code == 200, f"Failed to fetch /auth/me: {res.text}"
    assert res.json()["email"] == test_email, "Email mismatch"
    print("? GET /auth/me returns 200 and correct user profile")
    
    # 6. Logout
    res = client.post("/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert res.status_code == 204, f"Failed to logout: {res.text}"
    print("? POST /auth/logout returns 204 No Content")
    
    print("\nAll API tests passed successfully!")

if __name__ == '__main__':
    try:
        run_tests()
    except AssertionError as e:
        import sys
        print(f"? Test Failed: {e}")
        sys.exit(1)
