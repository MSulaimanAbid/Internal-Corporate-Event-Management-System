"""
services.py — Business Logic Layer

This module is the bridge between the HTTP routes (main.py) and the database
(models.py).  All database reads and writes go through here, keeping the route
handlers thin and the logic testable in isolation.

Responsibilities:
  - Execute SQLAlchemy queries against the `events` and `registrations` tables.
  - Enforce business rules (e.g. returning None when a record is not found so
    the route can respond with the right HTTP status code).
  - Handle partial updates by only writing fields the client actually sent.

Design principle:
  Services receive an open Session from the route via `Depends(get_db)` and
  are responsible for calling `db.commit()` / `db.refresh()` after any write.
  They never open their own sessions — that keeps transaction control clear.
"""

from sqlalchemy.orm import Session

# `models` gives us the SQLAlchemy ORM classes (Event, Registration).
import models

# `schemas` gives us the Pydantic types used for input validation.
import schemas


def get_events(db: Session, skip: int = 0, limit: int = 100):
    """
    Retrieve a paginated list of all events.

    Inputs:
        db   (Session) — Active SQLAlchemy session injected by FastAPI.
        skip (int)     — Number of rows to skip; used for offset-based pagination.
                         Defaults to 0 (start from the first row).
        limit (int)    — Maximum number of rows to return.
                         Defaults to 100 to prevent accidentally fetching the whole table.

    Outputs:
        list[models.Event] — All Event ORM objects in the requested page;
                             empty list if no events exist yet.

    Why we need it:
        Powers the GET /events endpoint; pagination keeps response sizes
        manageable as the event count grows.
    """
    return db.query(models.Event).offset(skip).limit(limit).all()


def get_event(db: Session, event_id: int):
    """
    Retrieve a single event by its primary key.

    Inputs:
        db       (Session) — Active SQLAlchemy session injected by FastAPI.
        event_id (int)     — The primary key of the event to look up.

    Outputs:
        models.Event | None — The matching Event ORM object, or None if no
                              event with that id exists.

    Why we need it:
        Used directly by the GET /events/{id} endpoint, and also called
        internally by update_event and delete_event to check existence before
        acting — avoids duplicating the lookup query in multiple places.
    """
    # `.first()` returns None instead of raising an exception when no row matches,
    # which lets the caller decide the appropriate HTTP response (404, etc.).
    return db.query(models.Event).filter(models.Event.id == event_id).first()


def create_event(db: Session, event: schemas.EventCreate):
    """
    Insert a new event row into the database.

    Inputs:
        db    (Session)           — Active SQLAlchemy session injected by FastAPI.
        event (schemas.EventCreate) — Validated Pydantic object containing the
                                      fields for the new event.

    Outputs:
        models.Event — The newly created Event ORM object, refreshed from the DB
                       so it includes the auto-generated `id`.

    Why we need it:
        Powers the POST /events endpoint; separating creation logic from the
        route handler keeps the handler one line and makes this testable directly.
    """
    # Convert Pydantic schema to an SQLAlchemy model dictionary
    # `model_dump()` turns the Pydantic object into a plain dict that
    # `**` unpacks into the Event constructor's keyword arguments.
    db_event = models.Event(**event.model_dump())

    db.add(db_event)      # Stage the new row in the session (not yet in DB).
    db.commit()           # Flush the INSERT to PostgreSQL and commit the transaction.
    db.refresh(db_event)  # Reload the row from DB so `db_event.id` is populated.
    return db_event


def update_event(db: Session, event_id: int, event_update: schemas.EventUpdate):
    """
    Partially update an existing event's fields.

    Inputs:
        db           (Session)            — Active SQLAlchemy session injected by FastAPI.
        event_id     (int)                — Primary key of the event to update.
        event_update (schemas.EventUpdate) — Pydantic object containing only the
                                            fields the client wants to change
                                            (all fields are optional in EventUpdate).

    Outputs:
        models.Event | None — The updated Event ORM object (refreshed from DB),
                              or None if no event with event_id exists.

    Why we need it:
        Powers the PUT /events/{id} endpoint.  Returning None instead of raising
        an exception keeps the service layer decoupled from HTTP concerns — the
        route translates None into a 404 response.
    """
    # Reuse get_event to avoid duplicating the SELECT query.
    db_event = get_event(db, event_id)
    if not db_event:
        # Signal to the caller that the event doesn't exist — route returns 404.
        return None

    # Only update fields that were actually provided in the request.
    # `exclude_unset=True` omits fields the client left out entirely,
    # so we don't accidentally overwrite existing data with None.
    update_data = event_update.model_dump(exclude_unset=True)

    # Apply each provided field to the ORM object using setattr so SQLAlchemy
    # tracks the change and includes it in the next commit.
    for key, value in update_data.items():
        setattr(db_event, key, value)

    db.commit()           # Write the UPDATE statement to PostgreSQL.
    db.refresh(db_event)  # Reload so the returned object reflects the saved state.
    return db_event


def delete_event(db: Session, event_id: int):
    """
    Delete an event and all its registrations from the database.

    Inputs:
        db       (Session) — Active SQLAlchemy session injected by FastAPI.
        event_id (int)     — Primary key of the event to delete.

    Outputs:
        bool — True if the event was found and deleted; False if no event with
               that id existed (lets the route return 404).

    Why we need it:
        Powers the DELETE /events/{id} endpoint.  The cascade="all, delete-orphan"
        setting on Event.Registrations (defined in models.py) means SQLAlchemy
        automatically deletes all Registration rows linked to this event in the
        same transaction — no manual cleanup needed here.
    """
    # Look up the event first; if it doesn't exist we can't delete it.
    db_event = get_event(db, event_id)
    if not db_event:
        # Return False so the route can respond with 404 instead of silently succeeding.
        return False

    db.delete(db_event)  # Mark the row for deletion; cascade removes registrations too.
    db.commit()          # Execute the DELETE and commit the transaction.
    return True          # Signal success to the route handler.
