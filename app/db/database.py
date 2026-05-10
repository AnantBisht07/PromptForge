from sqlalchemy import inspect, text
from sqlmodel import SQLModel, Session, create_engine, select
from app.core.config import settings
from app.db.models import Prompt, User, Workspace, WorkspaceMember

# echo=True logs every SQL statement — great for learning, turn off in production
engine = create_engine(settings.DATABASE_URL, echo=True)


def create_db_and_tables():
    """
    Create all tables defined in models.py.
    SQLModel reads the SQLModel subclasses that have table=True and
    generates the CREATE TABLE statements automatically.
    Called once on app startup.
    """
    SQLModel.metadata.create_all(engine)
    _ensure_prompt_collaboration_columns()
    _backfill_default_workspaces()


def _ensure_prompt_collaboration_columns():
    """
    Lightweight compatibility for local teaching databases.

    SQLModel can create new tables, but it will not alter an existing prompt
    table. These columns are required by workspace-scoped prompt queries.
    """
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "prompt" not in inspector.get_table_names():
            return

        existing_columns = {
            column["name"] for column in inspector.get_columns("prompt")
        }
        if "workspace_id" not in existing_columns:
            connection.execute(text("ALTER TABLE prompt ADD COLUMN workspace_id INTEGER"))
        if "status" not in existing_columns:
            connection.execute(
                text("ALTER TABLE prompt ADD COLUMN status VARCHAR DEFAULT 'review'")
            )
            connection.execute(
                text("UPDATE prompt SET status = 'review' WHERE status IS NULL")
            )


def _backfill_default_workspaces():
    """
    Give pre-collaboration users and prompts a workspace scope.
    """
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        for user in users:
            membership = session.exec(
                select(WorkspaceMember).where(WorkspaceMember.user_id == user.id)
            ).first()
            if membership:
                continue

            workspace = Workspace(
                name=f"{user.username}'s Workspace",
                owner_id=user.id,
            )
            session.add(workspace)
            session.commit()
            session.refresh(workspace)
            session.add(
                WorkspaceMember(
                    workspace_id=workspace.id,
                    user_id=user.id,
                    role="admin",
                )
            )
            session.commit()

        prompts = session.exec(
            select(Prompt).where(Prompt.workspace_id.is_(None))
        ).all()
        for prompt in prompts:
            membership = session.exec(
                select(WorkspaceMember)
                .where(WorkspaceMember.user_id == prompt.user_id)
                .order_by(WorkspaceMember.id.desc())
            ).first()
            if membership:
                prompt.workspace_id = membership.workspace_id
            if not prompt.status:
                prompt.status = "review"
            session.add(prompt)
        session.commit()


def get_session():
    """
    FastAPI dependency that provides a database session per request.

    Usage in a router:
        def my_route(session: Session = Depends(get_session)):
            ...

    The 'with' block ensures the session is closed (and the connection
    returned to the pool) even if an exception is raised.
    """
    with Session(engine) as session:
        yield session



