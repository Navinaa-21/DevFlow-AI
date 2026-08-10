from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
import os
from app.core.config import settings
from app.db.session import get_db

# Initialize the FastAPI App using APP_NAME from settings
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
)

# Configure CORS for local development (e.g. VS Code Live Server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with your actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temporary debug middleware to log OAuth-related session and cookie lifecycle (raw ASGI)
class OAuthDebugMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and "auth/github" in scope.get("path", ""):
            print(f"OAUTH_DEBUG [START]: Path: {scope.get('path')} | Scheme: {scope.get('scheme')}", flush=True)
            headers = {k.decode("latin1"): v.decode("latin1") for k, v in scope.get("headers", [])}
            print(f"OAUTH_DEBUG [HEADERS]: {headers}", flush=True)
            
            # Print session before (if already populated by SessionMiddleware)
            session = scope.get("session")
            print(f"OAUTH_DEBUG [SESSION BEFORE]: {session}", flush=True)

            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    print(f"OAUTH_DEBUG [RESPONSE STATUS]: {message.get('status')}", flush=True)
                    resp_headers = {k.decode("latin1"): v.decode("latin1") for k, v in message.get("headers", [])}
                    print(f"OAUTH_DEBUG [RESPONSE HEADERS]: {resp_headers}", flush=True)
                await send(message)

            await self.app(scope, receive, send_wrapper)
            
            # Print session after (if modified by route handler)
            print(f"OAUTH_DEBUG [SESSION AFTER]: {scope.get('session')}", flush=True)
        else:
            await self.app(scope, receive, send)

app.add_middleware(OAuthDebugMiddleware)

# Configure Starlette SessionMiddleware with secure cookies for production
app.add_middleware(
    SessionMiddleware, 
    secret_key=settings.SESSION_SECRET_KEY,
    https_only=not settings.DEBUG,
    same_site="lax"
)

# Custom ASGI middleware to correctly detect HTTPS scheme behind reverse proxies (like Render)
class ProxyHeadersMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            for header_name, header_value in scope.get("headers", []):
                if header_name == b"x-forwarded-proto":
                    scope["scheme"] = header_value.decode("latin1")
                    break
        await self.app(scope, receive, send)

app.add_middleware(ProxyHeadersMiddleware)

from app.api.webhook import router as webhook_router
app.include_router(webhook_router)

from app.api.auth import router as auth_router
app.include_router(auth_router, prefix="/api/v1/auth", tags=["authentication"])

from app.api.github import router as github_router
app.include_router(github_router, prefix="/api/v1/github", tags=["github"])

from app.api.commits import router as commits_router
app.include_router(commits_router, prefix="/commits", tags=["commits"])

from app.api.documentation import router as documentation_router
app.include_router(documentation_router, prefix="/documentation", tags=["documentation"])

from app.api.repositories import router as repositories_router
app.include_router(repositories_router, prefix="/repositories", tags=["repositories"])

from app.api.dashboard import router as dashboard_router
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])

from app.api.activity import router as activity_router
app.include_router(activity_router, prefix="/activity", tags=["activity"])


@app.get("/health", status_code=status.HTTP_200_OK)
async def db_health_check(db: Session = Depends(get_db)) -> dict:
    """
    Performs a live database connection check by running 'SELECT 1'.
    """
    try:
        # Run a simple check query synchronously against the database
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        # Raise 503 Service Unavailable on database connection failure
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed"
        )

# Mount the static frontend directory relative to this file's directory
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

