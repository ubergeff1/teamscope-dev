"""
Database engine and session setup using SQLAlchemy.

This module configures the SQLAlchemy ORM layer for the entire application.
It provides three things:

  1. ``engine`` -- The SQLAlchemy Engine connected to the database specified by
     the ``DATABASE_URL`` environment variable (see config.py). The engine
     manages a connection pool and handles low-level DBAPI communication.

  2. ``SessionLocal`` -- A configured session factory. Each call to
     ``SessionLocal()`` creates a new Session bound to the engine. Sessions
     are configured with:
       - autocommit=False: Transactions must be explicitly committed.
       - autoflush=False: Pending changes are not automatically flushed to the
         DB before queries. This gives the application explicit control over
         when writes happen.

  3. ``Base`` -- The declarative base class that all ORM models inherit from.
     SQLAlchemy uses this to maintain a registry of all model classes and their
     table metadata.

  4. ``get_db()`` -- A FastAPI dependency generator that provides a database
     session to route handlers and ensures it is closed after the request.

Connection pool behavior:
  - ``pool_pre_ping=True`` enables a lightweight "SELECT 1" check before
    reusing a pooled connection. This prevents errors from stale or dropped
    connections (e.g., after a database restart or network interruption).

All routers use ``get_db`` as a FastAPI dependency to get a database session.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

# Create the SQLAlchemy engine using the connection string from environment config.
# pool_pre_ping=True ensures connections are validated before use, avoiding
# "connection closed" errors from stale pooled connections.
engine = create_engine(settings.database_url, pool_pre_ping=True)

# Session factory -- creates new Session instances bound to the engine.
# autocommit=False means we use explicit transactions (session.commit()).
# autoflush=False prevents automatic SQL emission before queries, giving us
# full control over when pending ORM changes are flushed to the database.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base class that all database models inherit from.

    SQLAlchemy uses this class to:
      - Maintain a metadata registry of all tables and their columns.
      - Enable the declarative mapping style where models are defined as Python
        classes with Column attributes.
      - Support ``Base.metadata.create_all(engine)`` to auto-create tables.
    """
    pass


def get_db():
    """FastAPI dependency -- yields a database session and ensures cleanup.

    Usage in a route handler::

        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    The generator pattern (yield + finally) ensures the session is always closed
    after the request completes, even if an exception occurs. This prevents
    connection leaks back to the pool.

    Yields:
        A SQLAlchemy Session instance.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
