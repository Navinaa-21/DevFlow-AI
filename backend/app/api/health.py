import time
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import get_db

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def health_check(db: Session = Depends(get_db)):
    """Simple check that confirms FastAPI is alive and has a working database connection."""
    start_time = time.time()
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
        
    duration = time.time() - start_time
    
    overall_status = "healthy" if db_status == "healthy" else "unhealthy"
    status_code = status.HTTP_200_OK if overall_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "timestamp": time.time(),
            "services": {
                "api": "healthy",
                "database": {
                    "status": db_status,
                    "latency_ms": round(duration * 1000, 2)
                }
            }
        }
    )


@router.get("/database")
def database_health_check(db: Session = Depends(get_db)):
    """Detailed health check for the database, returning connection state, select 1, version, and latency."""
    start_time = time.time()
    try:
        select_1_res = db.execute(text("SELECT 1")).scalar()
        db_version = db.execute(text("SELECT version();")).scalar()
        latency_ms = round((time.time() - start_time) * 1000, 2)
        
        return {
            "status": "healthy",
            "connection": "successful",
            "select_1": select_1_res,
            "version": db_version,
            "latency_ms": latency_ms
        }
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "connection": "failed",
                "error": str(e),
                "latency_ms": latency_ms
            }
        )
