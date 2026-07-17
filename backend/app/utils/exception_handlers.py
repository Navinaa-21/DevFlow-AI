from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    NoResultFound,
    MultipleResultsFound,
)
from app.services.workspace_service import (
    WorkspaceNotFoundError,
    WorkspaceSlugConflictError,
    WorkspacePermissionError,
    WorkspaceMembershipConflictError,
)
from app.services.auth_service import AuthDomainError
from app.services.repository_service import (
    RepositoryNotFoundError as RepoServiceRepoNotFoundError,
    WorkspaceAccessDeniedError,
    GitHubTokenMissingError,
    GitHubConnectionError,
    RepositoryAlreadyExistsError,
)
from app.services.webhook_service import (
    WebhookServiceError,
    InvalidSignatureError,
    PayloadParseError,
    RepositoryNotFoundError as WebhookRepoNotFoundError
)


def db_integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    orig_msg = str(exc.orig) if exc.orig else str(exc)
    pgcode = getattr(exc.orig, "pgcode", None)

    # Postgres pgcode mappings (psycopg3 compatible)
    if pgcode == "23505" or "unique constraint" in orig_msg.lower():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Unique constraint violation. A record with this value already exists."}
        )
    elif pgcode == "23503" or "foreign key constraint" in orig_msg.lower():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Foreign key violation. The referenced record does not exist."}
        )
    elif pgcode == "23502" or "not-null constraint" in orig_msg.lower():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Null constraint violation. A required field is missing."}
        )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": f"Database integrity violation: {orig_msg}"}
    )


def db_operational_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database service is temporarily unavailable. Please try again later."}
    )


def db_no_result_found_handler(request: Request, exc: NoResultFound) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "The requested record was not found."}
    )


def db_multiple_results_found_handler(request: Request, exc: MultipleResultsFound) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": "Multiple records found where only one was expected."}
    )


def register_db_exception_handlers(app: FastAPI) -> None:
    """Registers database exception handlers onto the FastAPI application."""
    app.add_exception_handler(IntegrityError, db_integrity_error_handler)
    app.add_exception_handler(OperationalError, db_operational_error_handler)
    app.add_exception_handler(NoResultFound, db_no_result_found_handler)
    app.add_exception_handler(MultipleResultsFound, db_multiple_results_found_handler)
    
    # Workspace Domain Exceptions mappings
    app.add_exception_handler(
        WorkspaceNotFoundError,
        lambda r, e: JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(e)})
    )
    app.add_exception_handler(
        WorkspacePermissionError,
        lambda r, e: JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(e)})
    )
    app.add_exception_handler(
        WorkspaceMembershipConflictError,
        lambda r, e: JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(e)})
    )
    app.add_exception_handler(
        WorkspaceSlugConflictError,
        lambda r, e: JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(e)})
    )
    app.add_exception_handler(
        AuthDomainError,
        lambda r, e: JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(e)})
    )
    app.add_exception_handler(
        RepoServiceRepoNotFoundError,
        lambda r, e: JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(e)})
    )
    app.add_exception_handler(
        WorkspaceAccessDeniedError,
        lambda r, e: JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(e)})
    )
    app.add_exception_handler(
        GitHubTokenMissingError,
        lambda r, e: JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(e)})
    )
    app.add_exception_handler(
        GitHubConnectionError,
        lambda r, e: JSONResponse(status_code=status.HTTP_502_BAD_GATEWAY, content={"detail": str(e)})
    )
    app.add_exception_handler(
        RepositoryAlreadyExistsError,
        lambda r, e: JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(e)})
    )
    
    # Webhook Domain Exceptions mappings
    app.add_exception_handler(
        InvalidSignatureError,
        lambda r, e: JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(e)})
    )
    app.add_exception_handler(
        PayloadParseError,
        lambda r, e: JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(e)})
    )
    app.add_exception_handler(
        WebhookRepoNotFoundError,
        lambda r, e: JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(e)})
    )
    app.add_exception_handler(
        WebhookServiceError,
        lambda r, e: JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": str(e)})
    )
