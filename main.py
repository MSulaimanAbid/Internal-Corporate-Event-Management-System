"""
main.py — FastAPI Application Entry Point & Route Definitions

This is the top-level module that:
  1. Creates the FastAPI application instance with its metadata.
  2. Bootstraps the database schema on startup (creates tables if they don't exist).
  3. Declares all HTTP route handlers for the Events and Registrations resources.

Layer responsibilities (read alongside the other modules):
  main.py      → receives HTTP requests, validates input (via Pydantic schemas),
                  delegates to services.py, returns HTTP responses.
  services.py  → contains all DB queries and business logic.
  schemas.py   → defines request/response shapes and validation rules.
  models.py    → defines the ORM table structure.
  db.py        → manages the DB connection, engine, and session lifecycle.

Current endpoints:
  POST   /events                       → create a new event
  GET    /events                       → list all events (paginated)
  GET    /events/{id}                  → get a single event by id
  PUT    /events/{id}                  → partially update an event by id
  DELETE /events/{id}                  → delete an event (and its registrations) by id
  POST   /events/{id}/registrations   → register an employee for an event
  GET    /events/{id}/registrations   → list all registrations for an event
  DELETE /registrations/{id}          → cancel a specific registration by id

To run the app locally:
    uvicorn main:app --reload
Interactive docs are available at http://127.0.0.1:8000/docs
"""

# Local modules — order matters for circular-import avoidance:
# models must be imported before create_all so SQLAlchemy knows all table definitions.
import models
import schemas
import services
from db import engine, get_db
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

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


from datetime import date as date_type


@app.get("/events", response_model=list[schemas.EventResponse])
def read_events(
    skip: int = 0,
    limit: int = 10,
    title: str | None = None,
    date: date_type | None = None,
    db: Session = Depends(get_db),
):
    return services.get_events(db, skip=skip, limit=limit, title=title, event_date=date)


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


# ---------------------------------------------
# REGISTRATION ENDPOINTS
# ---------------------------------------------


@app.post(
    "/events/{id}/registrations",
    response_model=schemas.RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_for_event(
    id: int, registration: schemas.RegistrationCreate, db: Session = Depends(get_db)
):
    """
    Register an employee for a specific event.

    Inputs:
        id           (int, path)           — Primary key of the event to register for.
        registration (RegistrationCreate)  — Request body containing the employee's email.
        db           (Session)             — DB session injected by FastAPI via Depends(get_db).

    Outputs:
        RegistrationResponse (HTTP 201) — The created registration (id, employee_email, event_id).
        HTTP 404 Not Found              — If the event_id does not exist.
        HTTP 409 Conflict               — If the event is at full capacity OR the employee
                                          has already registered for this event.

    Why we need it:
        The primary action employees perform — signing up for an event.
        Three business rules are enforced by services.create_registration (event exists,
        capacity not exceeded, no duplicate); this route translates those outcomes
        into the appropriate HTTP responses using sentinel return values.
    """
    result = services.create_registration(db=db, event_id=id, registration=registration)

    if result is None:
        # services returned None → the event_id doesn't exist in the DB.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )
    if result == "CAPACITY_REACHED":
        # services returned this sentinel → event already has max_capacity registrations.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Event capacity reached"
        )
    if result == "DUPLICATE":
        # services returned this sentinel → this employee is already registered.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee already registered for this event",
        )

    # All checks passed — return the new registration object (serialized via RegistrationResponse).
    return result


@app.get(
    "/events/{id}/registrations", response_model=list[schemas.RegistrationResponse]
)
def view_event_registrations(id: int, db: Session = Depends(get_db)):
    """
    Retrieve the full attendee list for a specific event.

    Inputs:
        id (int, path) — Primary key of the event whose registrations to list.
        db (Session)   — DB session injected by FastAPI via Depends(get_db).

    Outputs:
        list[RegistrationResponse] (HTTP 200) — All registrations for the event;
                                                empty list if nobody has registered yet.
        HTTP 404 Not Found                    — If no event with the given id exists.

    Why we need it:
        Lets admins see who has signed up for an event, e.g. to prepare name badges,
        send reminders, or check whether capacity is filling up.
        We verify the event exists first so we return 404 (not an empty list) for
        an invalid id — an empty list would be misleading.
    """
    # Verify the event exists first — we want 404 for a bad id, not an empty list.
    db_event = services.get_event(db, event_id=id)
    if db_event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Event not found"
        )

    # Event confirmed to exist; fetch all its registrations.
    return services.get_event_registrations(db=db, event_id=id)


@app.delete("/registrations/{id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_registration(id: int, db: Session = Depends(get_db)):
    """
    Cancel (delete) a specific registration by its own id.

    Inputs:
        id (int, path) — Primary key of the Registration row to cancel.
        db (Session)   — DB session injected by FastAPI via Depends(get_db).

    Outputs:
        HTTP 204 No Content — Success; no body is returned (standard for DELETE).
        HTTP 404 Not Found  — If no registration with the given id exists.

    Why we need it:
        Allows an employee or admin to cancel a sign-up for an event.
        Uses the registration's own id (not event_id + email) so the caller doesn't
        need to know which event it belongs to — just the registration id from a
        previous GET or POST response.
    """
    success = services.delete_registration(db=db, registration_id=id)
    if not success:
        # services returned False → no registration row with this id exists.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found"
        )
