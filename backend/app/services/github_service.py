import httpx
from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.config import settings

class GithubService:
    """
    Service responsible for communicating directly with the GitHub API
    using the authenticated user's OAuth tokens.
    """
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.access_token = self._get_access_token()
        self.base_url = "https://api.github.com"
        
    def _get_access_token(self) -> str:
        for account in self.user.oauth_accounts:
            if account.provider == "github":
                return account.access_token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No GitHub account linked."
        )
        
    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
    def fetch_user_repositories(self) -> List[dict]:
        """
        Fetches repositories the authenticated user has access to.
        """
        url = f"{self.base_url}/user/repos?visibility=all&per_page=100&sort=updated"
        with httpx.Client() as client:
            response = client.get(url, headers=self._get_headers())
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"GitHub API Error: {response.text}"
                )
            return response.json()
            
    def fetch_repository_metadata(self, github_repo_id: int) -> dict:
        """
        Fetches precise metadata for a given GitHub repository ID to verify access.
        """
        url = f"{self.base_url}/repositories/{github_repo_id}"
        with httpx.Client() as client:
            response = client.get(url, headers=self._get_headers())
            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Repository not found on GitHub or access denied."
                )
            elif response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"GitHub API Error: {response.text}"
                )
            return response.json()
            
    def create_webhook(self, owner: str, repo: str, webhook_url: str) -> dict:
        """
        Creates a push webhook on the target repository pointing to DevFlow AI.
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/hooks"
        payload = {
            "name": "web",
            "active": True,
            "events": ["push"],
            "config": {
                "url": webhook_url,
                "content_type": "json",
                "secret": settings.GITHUB_WEBHOOK_SECRET,
                "insecure_ssl": "0"
            }
        }
        with httpx.Client() as client:
            response = client.post(url, headers=self._get_headers(), json=payload)
            if response.status_code not in (200, 201):
                # 422 could mean the webhook already exists. We parse it loosely.
                if response.status_code == 422:
                    return {"status": "already_exists"}
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to create GitHub webhook: {response.text}"
                )
            return response.json()
            
    def delete_webhook(self, owner: str, repo: str, webhook_url: str) -> bool:
        """
        Locates the DevFlow AI webhook by URL and deletes it from GitHub.
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/hooks"
        with httpx.Client() as client:
            response = client.get(url, headers=self._get_headers())
            if response.status_code == 404:
                return True # Repo doesn't exist anymore
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to fetch webhooks: {response.text}"
                )
                
            hooks = response.json()
            hook_id = None
            for hook in hooks:
                if hook.get("config", {}).get("url") == webhook_url:
                    hook_id = hook.get("id")
                    break
                    
            if not hook_id:
                return True # Nothing to delete
                
            delete_url = f"{self.base_url}/repos/{owner}/{repo}/hooks/{hook_id}"
            del_response = client.delete(delete_url, headers=self._get_headers())
            
            if del_response.status_code not in (204, 404):
                raise HTTPException(
                    status_code=del_response.status_code,
                    detail=f"Failed to delete GitHub webhook: {del_response.text}"
                )
                
            return True

    def fetch_commit_diff(self, owner: str, repo: str, sha: str) -> str:
        """
        Fetches the raw git diff for a specific commit SHA from GitHub.
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/commits/{sha}"
        headers = self._get_headers()
        headers["Accept"] = "application/vnd.github.v3.diff"
        with httpx.Client() as client:
            response = client.get(url, headers=headers)
            if response.status_code != 200:
                # Return empty string on error or if not accessible
                return ""
            return response.text
