"""
db.py — Database Configuration & Session Management

This module is the single source of truth for all database connectivity in the
Internal Corporate Event Management System.  It is responsible for:

  1. Loading the database connection URL from the environment (.env file).
  2. Creating the SQLAlchemy engine that talks to the PostgreSQL database.
  3. Providing a session factory (SessionLocal) used throughout the app to
     open and close database transactions safely.
  4. Defining the declarative base that all ORM models inherit from.
  5. Exposing a FastAPI-compatible dependency (`get_db`) that yields a session
     per request and guarantees the session is closed afterward.
  6. Providing a one-shot `create_tables()` helper for initial schema setup.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Load environment variables from the .env file into os.environ so we can
# read secrets (like the DB URL) without hardcoding them in the source code.
load_dotenv()

# Retrieve the full database connection string, e.g.:
#   postgresql://user:password@localhost:5432/event_db
# Keeping this in .env (and out of source control) prevents credential leaks.
SQL_URL = os.getenv(key="SQL_URL")

# The engine is the low-level connection pool to PostgreSQL.
# SQLAlchemy manages the pool internally; we just pass the URL.
engine = create_engine(SQL_URL)

# SessionLocal is the factory for individual database sessions.
#   autocommit=False → we control when transactions are committed (safer).
#   autoflush=False  → prevents SQLAlchemy from issuing SQL before we're ready.
#   bind=engine      → ties every session to our PostgreSQL engine.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# `base` is the parent class for all ORM models (Event, Registration, …).
# SQLAlchemy uses it to track table metadata and generate CREATE TABLE SQL.
base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a database session for a single request.

    Yields:
        db (Session): An active SQLAlchemy session bound to PostgreSQL.

    How it works:
        - Opens a new session at the start of each request.
        - `yield` hands the session to the route/service that declared this
          dependency via `Depends(get_db)`.
        - The `finally` block ensures the session is **always** closed after
          the request completes (even if an exception is raised), preventing
          connection leaks.

    Why we need it:
        FastAPI's dependency injection system calls this function automatically
        for every endpoint that lists it as a dependency, so we never forget to
        open or close the session.
    """
    db = SessionLocal()  # Open a new DB session for this request
    try:
        yield db  # Hand the session to the caller (route / service)
    finally:
        db.close()  # Always release the connection back to the pool


def create_tables():
    """
    Create all database tables defined by ORM models that inherit from `base`.

    Inputs:  None
    Outputs: None (side-effect: tables are created in the DB if they don't exist)

    How it works:
        SQLAlchemy inspects every model registered under `base` and issues
        CREATE TABLE IF NOT EXISTS statements for each one.

    Why we need it:
        Called once during initial project setup (or in CI) to provision the
        database schema without writing raw SQL.  Running it on an already
        provisioned DB is safe — existing tables are left untouched.
    """
    # Emit CREATE TABLE SQL for all models that have been imported and
    # registered against `base` (models must be imported before this runs).
    base.metadata.create_all(bind=engine)


# Allow running this file directly for a quick one-shot schema setup:
#   python db.py
# This is handy during local development or first-time deployment.
if __name__ == "__main__":
    create_tables()
    print("Tables created successfully.")
