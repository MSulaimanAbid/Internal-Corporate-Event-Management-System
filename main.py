"""
main.py — FastAPI Application Entry Point & Route Definitions

This is the top-level module that:
  1. Creates the FastAPI application instance with its metadata.
  2. Bootstraps the database schema on startup (creates tables if they don't exist).
  3. Declares all HTTP route handlers for the Events resource.

Layer responsibilities (read alongside the other modules):
  main.py      → receives HTTP requests, validates input (via Pydantic schemas),
                  delegates to services.py, returns HTTP responses.
  services.py  → contains all DB queries and business logic.
  schemas.py   → defines request/response shapes and validation rules.
  models.py    → defines the ORM table structure.
  db.py        → manages the DB connection, engine, and session lifecycle.

Current endpoints (all under /events):
  POST   /events          → create a new event
  GET    /events          → list all events (paginated)
  GET    /events/{id}     → get a single event by id
  PUT    /events/{id}     → partially update an event by id
  DELETE /events/{id}     → delete an event (and its registrations) by id

To run the app locally:
    uvicorn main:app --reload
Interactive docs are available at http://127.0.0.1:8000/docs
"""

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

# Local modules — order matters for circular-import avoidance:
# models must be imported before create_all so SQLAlchemy knows all table definitions.
import models
import schemas
import services
from db import engine, get_db

# Bootstrap the DB schema: issues CREATE TABLE IF NOT EXISTS for every model
# that inherits from `base`.  Safe to run on every startup — existing tables
# are left untouched.
# Create all database tables based on models.py
models.base.metadata.create_all(bind=engine)

# Instantiate the FastAPI app.  `title`, `description`, and `version` appear
# in the auto-generated OpenAPI docs at /docs and /redoc.
app = FastAPI(
    title="Corporate Event Management API",
    description="Acme Corp Internal Event System",
    version="1.0.0",
)

# ---------------------------------------------
# EVENT ENDPOINTS
# ---------------------------------------------


@app.post(
    "/events", response_model=schemas.EventResponse, status_code=status.HTTP_201_CREATED
)
def create_event(event: schemas.EventCreate, db: Session = Depends(get_db)):
    """
    Create a new corporate event.

    Inputs:
        event (EventCreate) — Request body; validated by Pydantic (title, description,
                              date, location, max_capacity — all required except description).
        db    (Session)     — DB session injected by FastAPI via Depends(get_db).

    Outputs:
        EventResponse (HTTP 201) — The newly created event, including its DB-assigned id.

    Why we need it:
        Entry point for admins to publish new events that employees can register for.
    """
    return services.create_event(db=db, event=event)


@app.get("/events", response_model=list[schemas.EventResponse])
def read_events(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """
    Retrieve a paginated list of all events.

    Inputs:
        skip  (int, query) — Number of records to skip; default 0.
        limit (int, query) — Max records to return; default 10.
        db    (Session)    — DB session injected by FastAPI via Depends(get_db).

    Outputs:
        list[EventResponse] (HTTP 200) — Array of event objects for the requested page;
                                         empty array if no events exist.

    Why we need it:
        Lets employees browse all upcoming events before deciding which to join.
        `skip`/`limit` allow front-end pagination without loading the full table.
    """
    return services.get_events(db, skip=skip, limit=limit)


@app.get("/events/{id}", response_model=schemas.EventResponse)
def read_event(id: int, db: Session = Depends(get_db)):
    """
    Retrieve the details of a single event.

    Inputs:
        id (int, path) — The primary key of the event to fetch.
        db (Session)   — DB session injected by FastAPI via Depends(get_db).

    Outputs:
        EventResponse (HTTP 200)  — Full event details if found.
        HTTP 404 Not Found        — If no event with the given id exists.

    Why we need it:
        Powers detail/confirmation pages where a user wants to see full info
        about one specific event before registering.
    """
    db_event = services.get_event(db, event_id=id)
    if db_event is None:
        # services.get_event returns None when the id doesn't match any row;
        # translate that into a proper HTTP 404 with a descriptive message.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return db_event


@app.put("/events/{id}", response_model=schemas.EventResponse)
def update_event(id: int, event: schemas.EventUpdate, db: Session = Depends(get_db)):
    """
    Partially update an existing event.

    Inputs:
        id    (int, path)   — Primary key of the event to update.
        event (EventUpdate) — Request body with only the fields to change
                              (all fields are optional in EventUpdate).
        db    (Session)     — DB session injected by FastAPI via Depends(get_db).

    Outputs:
        EventResponse (HTTP 200) — The updated event with refreshed field values.
        HTTP 404 Not Found       — If no event with the given id exists.

    Why we need it:
        Allows admins to correct event details (e.g. change venue or date)
        after publication without having to delete and recreate the event.
    """
    db_event = services.update_event(db, event_id=id, event_update=event)
    if db_event is None:
        # services.update_event returns None when the event doesn't exist;
        # surface that as a 404 so the client knows the id was invalid.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    return db_event


@app.delete("/events/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(id: int, db: Session = Depends(get_db)):
    """
    Delete an event and all its associated registrations.

    Inputs:
        id (int, path) — Primary key of the event to delete.
        db (Session)   — DB session injected by FastAPI via Depends(get_db).

    Outputs:
        HTTP 204 No Content — Success; no body is returned (standard for DELETE).
        HTTP 404 Not Found  — If no event with the given id exists.

    Why we need it:
        Lets admins remove cancelled or erroneous events.  The cascade setting on
        the Event model ensures all registrations for the event are removed in the
        same transaction, keeping the database consistent.
    """
    success = services.delete_event(db, event_id=id)
    if not success:
        # services.delete_event returns False when the event doesn't exist;
        # surface that as a 404 rather than silently succeeding.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
