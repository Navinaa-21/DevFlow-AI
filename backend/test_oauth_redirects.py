import requests

try:
    print("Testing Google OAuth endpoint...")
    res = requests.get("http://127.0.0.1:8000/auth/login/google", allow_redirects=False)
    print(res.status_code)
    if res.status_code == 302:
        print("? HTTP 302 Redirect received for Google")

    print("Testing GitHub OAuth endpoint...")
    res = requests.get("http://127.0.0.1:8000/auth/login/github", allow_redirects=False)
    print(res.status_code)
    if res.status_code == 302:
        print("? HTTP 302 Redirect received for GitHub")
except Exception as e:
    print(f"Error: {e}")
