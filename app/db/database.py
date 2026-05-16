from sqlalchemy import inspect, text
from sqlmodel import SQLModel, Session, create_engine, select

from app.core.config import settings
from app.db.models import Prompt, User, Workspace, WorkspaceMember

# SQL_ECHO logs every SQL statement when enabled for debugging.
engine = create_engine(settings.DATABASE_URL, echo=settings.SQL_ECHO)


def create_db_and_tables():
    """
    Create all tables defined in models.py.

    SQLModel can create new tables. The compatibility helpers below handle the
    small schema additions introduced during earlier workspace lessons.
    """
    SQLModel.metadata.create_all(engine)
    _ensure_prompt_collaboration_columns()
    _backfill_default_workspaces()


def _ensure_prompt_collaboration_columns():
    """
    Lightweight compatibility for local teaching databases.

    SQLModel creates new tables, but it will not alter an existing prompt
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
    """
    with Session(engine) as session:
        yield session
