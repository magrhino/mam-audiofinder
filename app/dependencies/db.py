"""
Database session provider dependencies.

Provides:
- db_session: Context-managed dependency for history.db
- covers_db_session: Context-managed dependency for covers.db
"""

from typing import Generator
from contextlib import contextmanager
from sqlalchemy.orm import Session

from db.db import engine, covers_engine


def db_session() -> Generator[Session, None, None]:
    """
    Provides a SQLAlchemy session for history.db.

    Handles transaction management and automatic cleanup.

    Yields:
        SQLAlchemy Session for history.db
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def covers_db_session() -> Generator[Session, None, None]:
    """
    Provides a SQLAlchemy session for covers.db.

    Handles transaction management and automatic cleanup.

    Yields:
        SQLAlchemy Session for covers.db
    """
    session = Session(covers_engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
