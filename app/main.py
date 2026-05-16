from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.db.database import create_db_and_tables
from app.middleware.logging_middleware import request_logging_middleware
from app.routers import (
    ab_test_router,
    activity_router,
    analytics_router,
    auth_router,
    eval_router,
    feedback_router,
    prompt_router,
    user_router,
    workspace_router,
)

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Create database tables on startup for this teaching project.
    """
    create_db_and_tables()
    yield


app = FastAPI(
    title="PromptForge API",
    description=(
        "Multi-tenant prompt management system with JWT auth, role-based "
        "access control, versioning, semantic search, evaluation, analytics, "
        "and collaboration workflows."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.middleware("http")(request_logging_middleware)

app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(workspace_router.router)
app.include_router(activity_router.router)
app.include_router(prompt_router.router)
app.include_router(eval_router.router)
app.include_router(ab_test_router.router)
app.include_router(analytics_router.router)
app.include_router(feedback_router.router)


@app.get("/", tags=["Health"])
def root():
    """Health-check endpoint."""
    return {
        "message": "PromptForge API is running",
        "docs": "/docs",
        "redoc": "/redoc",
    }
