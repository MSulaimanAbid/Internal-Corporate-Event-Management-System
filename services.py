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
  - Guard registrations against: non-existent events, full capacity, and
    duplicate sign-ups — returning sentinel strings so routes map them to the
    correct HTTP status codes without coupling this layer to FastAPI/HTTP.

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

    db.add(db_event)  # Stage the new row in the session (not yet in DB).
    db.commit()  # Flush the INSERT to PostgreSQL and commit the transaction.
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

    db.commit()  # Write the UPDATE statement to PostgreSQL.
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
    db.commit()  # Execute the DELETE and commit the transaction.
    return True  # Signal success to the route handler.


def create_registration(
    db: Session, event_id: int, registration: schemas.RegistrationCreate
):
    """
    Register an employee for an event, enforcing three business rules in order.

    Inputs:
        db           (Session)                   — Active SQLAlchemy session injected by FastAPI.
        event_id     (int)                        — Primary key of the event to register for.
        registration (schemas.RegistrationCreate) — Validated Pydantic object containing
                                                    the employee's email address.

    Outputs:
        models.Registration — The newly created Registration ORM object (refreshed from DB)
                              if all three rules pass.
        None                — If the event does not exist (route should return HTTP 404).
        "CAPACITY_REACHED"  — If the event is already at max_capacity (route returns HTTP 409).
        "DUPLICATE"         — If the employee has already registered for this event (HTTP 409).

    Why we need it:
        A single registration attempt must satisfy three sequential guards before
        writing to the DB.  Keeping these checks here (not in the route) means
        the logic is testable without spinning up an HTTP server, and the route
        stays a thin translator from service output → HTTP response.
    """
    # Rule 1: Check if event exists
    # We must confirm the event is real before checking anything else.
    db_event = get_event(db, event_id)
    if not db_event:
        return None  # Will trigger a 404 Not Found

    # Rule 2: Check event capacity
    # Count how many registrations already exist for this event and compare
    # against max_capacity.  Using .count() is more efficient than loading all rows.
    current_count = (
        db.query(models.Registration)
        .filter(models.Registration.event_id == event_id)
        .count()
    )
    if current_count >= db_event.max_capacity:
        return "CAPACITY_REACHED"  # Will trigger a 409 Conflict

    # Rule 3: Check for duplicate registration
    # The DB also enforces uniqueness via the `employee_event_unique` constraint,
    # but checking here first lets us return a clear sentinel instead of catching
    # an IntegrityError, which is harder to map to a specific error message.
    existing_reg = (
        db.query(models.Registration)
        .filter(
            models.Registration.event_id == event_id,
            models.Registration.employee_email == registration.employee_email,
        )
        .first()
    )
    if existing_reg:
        return "DUPLICATE"  # Will trigger a 409 Conflict

    # All checks passed, create registration
    # `model_dump()` converts the Pydantic object to a dict; we also pass event_id
    # separately because it comes from the URL path, not the request body.
    db_registration = models.Registration(
        **registration.model_dump(), event_id=event_id
    )
    db.add(db_registration)  # Stage the INSERT in the session.
    db.commit()  # Persist to PostgreSQL.
    db.refresh(db_registration)  # Reload so the returned object has its DB-assigned id.
    return db_registration


def get_event_registrations(db: Session, event_id: int):
    """
    Retrieve all registrations for a specific event.

    Inputs:
        db       (Session) — Active SQLAlchemy session injected by FastAPI.
        event_id (int)     — Primary key of the event whose registrations to fetch.

    Outputs:
        list[models.Registration] — All Registration rows linked to this event;
                                    empty list if nobody has registered yet.

    Why we need it:
        Powers the GET /events/{id}/registrations endpoint so admins can see
        a full attendee list for any event.  The caller (route) is responsible
        for verifying the event exists before calling this function.
    """
    # Filter registrations by event_id; `.all()` returns a list (never None).
    return (
        db.query(models.Registration)
        .filter(models.Registration.event_id == event_id)
        .all()
    )


def delete_registration(db: Session, registration_id: int):
    """
    Cancel (delete) a single registration by its primary key.

    Inputs:
        db              (Session) — Active SQLAlchemy session injected by FastAPI.
        registration_id (int)     — Primary key of the registration row to remove.

    Outputs:
        bool — True if the registration was found and deleted successfully;
               False if no registration with that id exists (route returns HTTP 404).

    Why we need it:
        Powers the DELETE /registrations/{id} endpoint, allowing an employee or
        admin to cancel a specific registration without affecting the parent event
        or other registrations for the same event.
    """
    # Look up the registration by its own id (not event_id) so the caller
    # can cancel any registration they know the id of, regardless of event.
    db_registration = (
        db.query(models.Registration)
        .filter(models.Registration.id == registration_id)
        .first()  # Returns None if no matching row — avoids raising an exception.
    )
    if not db_registration:
        # Signal to the route that the id was invalid — route returns 404.
        return False

    db.delete(db_registration)  # Mark the row for deletion in the session.
    db.commit()  # Execute the DELETE and commit the transaction.
    return True  # Signal success to the route handler.
