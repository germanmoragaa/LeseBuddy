from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api import articles, auth, users, vocabulary
from app.core.db import get_db

app = FastAPI(title="LeseBuddy API", version="0.1.0")
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(articles.router)
app.include_router(vocabulary.router)


@app.get("/api/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/health/db")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database unreachable") from exc
    return {"status": "ok"}
