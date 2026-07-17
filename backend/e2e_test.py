import asyncio
import httpx
import uuid
import os

BASE_URL = "http://127.0.0.1:8000"

async def run_tests():
    print("Starting E2E API Validation...")
    
    async with httpx.AsyncClient() as client:
        # TEST 2: Register
        email = f"e2e_{uuid.uuid4()}@example.com"
        password = "password123"
        print(f"Registering {email}")
        
        reg_res = await client.post(f"{BASE_URL}/auth/register", json={
            "full_name": "E2E Test User",
            "email": email,
            "password": password
        })
        assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
        tokens = reg_res.json()
        assert "access_token" in tokens
        print("Registration successful, JWT returned.")
        
        # TEST 3: Login
        login_res = await client.post(f"{BASE_URL}/auth/login", json={
            "email": email,
            "password": password
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        tokens = login_res.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        print("Login successful, JWT returned.")
        
        # TEST 11: JWT APIs
        # /auth/me
        me_res = await client.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {access_token}"})
        assert me_res.status_code == 200, f"/auth/me failed: {me_res.text}"
        me_data = me_res.json()
        assert me_data["email"] == email
        print("/auth/me successful.")
        
        # /auth/refresh
        refresh_res = await client.post(f"{BASE_URL}/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert refresh_res.status_code == 200, f"/auth/refresh failed: {refresh_res.text}"
        new_tokens = refresh_res.json()
        assert "access_token" in new_tokens
        print("/auth/refresh successful.")
        
        # /auth/logout
        logout_res = await client.post(f"{BASE_URL}/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
        assert logout_res.status_code == 204, f"/auth/logout failed: {logout_res.text}"
        print("/auth/logout successful.")
        
        # OpenAPI (Swagger) Test
        openapi_res = await client.get(f"{BASE_URL}/openapi.json")
        assert openapi_res.status_code == 200
        openapi_data = openapi_res.json()
        paths = openapi_data.get("paths", {})
        assert "/auth/login" in paths
        assert "/auth/register" in paths
        print("OpenAPI schema verified.")

        print("All API E2E Tests Passed!")

if __name__ == "__main__":
    asyncio.run(run_tests())
