"""
Database Engine & Session Management (SQLite)

Provides the SQLAlchemy async engine, session factory, and a helper
to create all tables on startup.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# SQLite database file lives next to the project root
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "nexus.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables (safe to call multiple times)."""
    from src.db.models import Project, Repository, RepoConnection, Commit, ImpactReport  # noqa
    Base.metadata.create_all(bind=engine)
