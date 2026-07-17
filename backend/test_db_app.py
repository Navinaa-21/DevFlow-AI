from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

app = FastAPI(title="Minimal DB Test App")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/db-status")
def check_db_status(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT version();")).scalar()
        return {
            "status": "success",
            "message": "FastAPI database connection is working!",
            "database_version": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
