from sqlmodel import SQLModel, create_engine, Session
from app.core.config import settings

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




