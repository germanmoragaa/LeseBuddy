from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api import articles, auth, reviews, users, vocabulary
from app.core.db import get_db

app = FastAPI(title="LeseBuddy API", version="0.1.0")
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(articles.router)
app.include_router(vocabulary.router)
app.include_router(reviews.router)

# SQLSTATEs a cancelled query surfaces as when app/core/db.py's statement_timeout/lock_timeout
# fire — e.g. another session (a stuck import transaction, in the incident that prompted
# this) holding a lock on the rows being read.
_LOCK_TIMEOUT_SQLSTATE = "55P03"  # lock_not_available
_STATEMENT_TIMEOUT_SQLSTATE = "57014"  # query_canceled


@app.exception_handler(OperationalError)
def handle_operational_error(request: Request, exc: OperationalError) -> JSONResponse:
    """Maps a cancelled query (our own statement_timeout/lock_timeout firing, most likely
    because something else is holding a lock on the rows being read) to a clean, typed JSON
    error instead of a 500 with a raw stack trace. Any other OperationalError (e.g. the DB
    being down) also lands here rather than leaking driver internals to the client."""
    sqlstate = getattr(exc.orig, "sqlstate", None)
    if sqlstate == _LOCK_TIMEOUT_SQLSTATE:
        return JSONResponse(
            status_code=503,
            content={
                "detail": {
                    "code": "database_busy",
                    "message": "The database is busy right now. Please try again.",
                }
            },
        )
    if sqlstate == _STATEMENT_TIMEOUT_SQLSTATE:
        return JSONResponse(
            status_code=504,
            content={
                "detail": {
                    "code": "database_timeout",
                    "message": "That request took too long. Please try again.",
                }
            },
        )
    return JSONResponse(
        status_code=503,
        content={
            "detail": {
                "code": "database_unavailable",
                "message": "The database is temporarily unavailable. Please try again.",
            }
        },
    )


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
