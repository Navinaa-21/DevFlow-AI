from fastapi import FastAPI
from app.api.user import router as user_router
from app.api.workspace import invitation_router, router as workspace_router
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.repository import router as repository_router
from app.api.webhook import router as webhook_router
from app.api.dashboard import router as dashboard_router
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.utils.exception_handlers import register_db_exception_handlers
from app.core.config import settings

app = FastAPI(title="Demo Auth API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
)

register_db_exception_handlers(app)

app.include_router(user_router)
app.include_router(workspace_router)
app.include_router(invitation_router)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(repository_router)
app.include_router(webhook_router)
app.include_router(dashboard_router)


@app.get("/")
def root():
    return {
        "message": "Backend is running",
        "database": "PostgreSQL connected"
    }
