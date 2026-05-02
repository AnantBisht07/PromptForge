from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.database import create_db_and_tables
from app.routers import auth_router, user_router, prompt_router, eval_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Code before 'yield' runs at startup.
    Code after 'yield' runs at shutdown.

    We use this to create DB tables once when the server starts —
    equivalent to running migrations in a simple setup.
    """
    create_db_and_tables()
    yield
    # Nothing to clean up for now (connection pool is managed by SQLModel)


app = FastAPI(
    title="PromptForge API",
    description=(
        "Multi-tenant prompt management system with JWT auth, "
        "role-based access control, versioning, and semantic search via Qdrant."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Register all routers — each handles a different domain
app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(prompt_router.router)
app.include_router(eval_router.router)


@app.get("/", tags=["Health"])
def root():
    """Health-check endpoint — also a quick way to verify the server is up."""
    return {
        "message": "PromptForge API is running",
        "docs": "/docs",
        "redoc": "/redoc",
    }
