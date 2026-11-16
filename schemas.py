"""
schemas.py — Pydantic Request / Response Schemas

This module defines all the data-validation and serialization contracts for the
Internal Corporate Event Management System API.  It sits between the HTTP layer
(main.py) and the business logic layer (services.py).

Responsibilities:
  - Validate incoming request bodies (create / update payloads).
  - Shape outgoing response bodies so only the right fields are exposed.
  - Keep validation rules (min_length, gt=0, EmailStr …) in one central place
    so routes and services stay clean.

Schema hierarchy:
    EventBase               ← shared fields for Event create/read
    ├── EventCreate         ← used as the request body when creating an event
    ├── EventUpdate         ← used as the request body for partial updates (all fields optional)
    └── EventResponse       ← returned to the client; adds `id`, enables ORM mode
            └── EventWithRegistrationsResponse  ← EventResponse + nested registrations list

    RegistrationBase        ← shared fields for Registration create/read
    ├── RegistrationCreate  ← used as the request body when registering for an event
    └── RegistrationResponse← returned to the client; adds `id` and `event_id`, enables ORM mode

Pydantic performs automatic type coercion and raises HTTP 422 Unprocessable Entity
for any request that fails these constraints — no manual validation needed in routes.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ---------------------------------
# EVENT SCHEMAS
# ---------------------------------


class EventBase(BaseModel):
    """
    Shared base schema for all event-related Pydantic models.

    Why it exists:
        Centralises the common field definitions (title, description, date,
        location, max_capacity) so that EventCreate, EventUpdate, and
        EventResponse don't duplicate them.  Any field-level constraint change
        only needs to be made here.

    Fields:
        title        (str)       — Human-readable event name; at least 1 character.
        description  (str|None)  — Optional longer description; defaults to None.
        date         (date)      — ISO-8601 date (YYYY-MM-DD) of the event.
        location     (str)       — Venue name or URL; at least 1 character.
        max_capacity (int)       — Positive integer cap on attendees (gt=0 enforced).
    """

    # `...` means the field is required (no default). min_length=1 rejects empty strings.
    title: str = Field(..., min_length=1, description="The title of the event.")

    # Optional field — omitting it in the request body is perfectly valid.
    description: str | None = Field(
        None, description="A detailed description of the event."
    )

    # Pydantic automatically parses "2025-06-15" strings into Python date objects.
    date: date = Field(
        ..., description="The date on which the event will take place(YYYY-MM-DD)."
    )

    # min_length=1 prevents whitespace-only strings from passing validation.
    location: str = Field(
        ..., min_length=1, description="The location where the event will be held."
    )

    # gt=0 means strictly greater than zero — 0-capacity events are rejected.
    max_capacity: int = Field(
        ..., gt=0, description="The maximum number of attendees allowed for the event."
    )


class EventCreate(EventBase):
    """
    Request schema for creating a new event.

    Inputs:  All fields from EventBase (title, description, date, location, max_capacity).
    Outputs: Used by FastAPI to parse and validate the JSON request body.

    Why it exists:
        Having a dedicated create schema (even if currently identical to EventBase)
        lets us add create-only fields later (e.g. a creator_id) without touching
        the base or the response schema.
    """

    pass  # Inherits all fields from EventBase — no extra fields needed at creation time.


class EventUpdate(EventBase):
    """
    Request schema for partially updating an existing event (HTTP PATCH).

    Inputs:  Any subset of event fields — every field is optional (type | None).
    Outputs: Used by FastAPI to parse the JSON request body; only provided fields
             should be applied by the service layer.

    Why it exists:
        Unlike EventCreate (which requires all fields), EventUpdate makes every
        field optional so the client can send only what changed.  The service
        layer is responsible for ignoring None values when writing to the DB.

    Fields (all optional):
        title        (str|None)  — New event title; min 1 char if provided.
        description  (str|None)  — New description.
        date         (date|None) — New event date in YYYY-MM-DD format.
        location     (str|None)  — New venue/URL; min 1 char if provided.
        max_capacity (int|None)  — New capacity cap; must be > 0 if provided.
    """

    # All fields shadow the required ones in EventBase and become optional (None = not changed).
    title: str | None = Field(None, min_length=1, description="The title of the event.")
    description: str | None = Field(
        None, description="A detailed description of the event."
    )
    date: date | None = Field(
        None, description="The date on which the event will take place(YYYY-MM-DD)."
    )
    location: str | None = Field(
        None, min_length=1, description="The location where the event will be held."
    )
    max_capacity: int | None = Field(
        None, gt=0, description="The maximum number of attendees allowed for the event."
    )


class EventResponse(EventBase):
    """
    Response schema returned to the client after any event read/create operation.

    Inputs:  An SQLAlchemy Event ORM object (via from_attributes=True).
    Outputs: JSON object with all EventBase fields plus the event's database `id`.

    Why it exists:
        Separating the response schema from the create schema ensures we never
        accidentally expose write-only fields, and always include the `id` that
        the client needs to reference the event in future requests.

    Extra fields (beyond EventBase):
        id (int) — The DB-assigned primary key of the event.

    ORM mode (from_attributes=True):
        Tells Pydantic to read data from SQLAlchemy model attributes rather than
        a dict, so we can pass ORM objects directly instead of converting manually.
    """

    # Added on top of EventBase — the DB-assigned primary key the client uses to
    # reference this event in update/delete/registration calls.
    id: int = Field(..., description="The unique identifier of the event.")

    # from_attributes=True (formerly orm_mode=True) lets Pydantic read SQLAlchemy
    # ORM object attributes directly instead of requiring a plain dict.
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------
# REGISTRATION SCHEMAS
# ---------------------------------


class RegistrationBase(BaseModel):
    """
    Shared base schema for all registration-related Pydantic models.

    Why it exists:
        Centralises the employee_email field so RegistrationCreate and
        RegistrationResponse don't duplicate its definition or validation rules.

    Fields:
        employee_email (EmailStr) — The registering employee's email address.
                                    Pydantic's EmailStr validates format automatically,
                                    rejecting malformed addresses before they reach the DB.
    """

    # EmailStr performs RFC-compliant email validation — no manual regex needed.
    employee_email: EmailStr = Field(
        ..., description="The email address of the employee registering for the event."
    )


class RegistrationCreate(RegistrationBase):
    """
    Request schema for registering an employee for an event.

    Inputs:  employee_email (str) — provided in the request body.
             event_id is taken from the URL path parameter, not the body.
    Outputs: Used by FastAPI to parse and validate the JSON request body.

    Why it exists:
        A dedicated create schema (even though currently identical to
        RegistrationBase) allows adding registration-specific fields later
        without breaking the base or response schema.
    """

    pass  # Inherits employee_email from RegistrationBase — no extra fields needed.


class RegistrationResponse(RegistrationBase):
    """
    Response schema returned to the client after a registration is created or read.

    Inputs:  An SQLAlchemy Registration ORM object (via from_attributes=True).
    Outputs: JSON object with employee_email, plus the registration's id and event_id.

    Why it exists:
        The client needs both `id` (to cancel/lookup the registration) and
        `event_id` (to know which event was registered for).  These are DB-side
        values not present in the create request, so they live in the response schema.

    Extra fields (beyond RegistrationBase):
        id       (int) — DB-assigned primary key of the registration row.
        event_id (int) — FK linking this registration to the parent Event.

    ORM mode (from_attributes=True):
        Allows Pydantic to read directly from SQLAlchemy Registration objects.
    """

    # DB-assigned primary key — the client uses this to reference the registration.
    id: int = Field(..., description="The unique identifier of the registration.")

    # Tells the client which event this registration belongs to.
    event_id: int = Field(
        ..., description="The ID of the event for which the registration is made."
    )

    # from_attributes=True lets Pydantic read SQLAlchemy ORM attributes directly.
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------
# EXTENDED EVENT SCHEMA (Optional but helpful)
# ---------------------------------------------
class EventWithRegistrationsResponse(EventResponse):
    """
    Extended response schema that nests an event's registrations inside the event payload.

    Inputs:  An SQLAlchemy Event ORM object that has its `Registrations` relationship
             eagerly or lazily loaded.
    Outputs: JSON with all EventResponse fields plus a `registrations` list, each
             item serialized as a RegistrationResponse.

    Why it exists:
        Useful for admin endpoints or detail views where the caller needs to see
        both the event details and who has registered — avoids a second API call.
        The default of `[]` means events with no registrations serialize cleanly.
    """

    # Nested list of registrations — defaults to empty list so the field is always present.
    registrations: list[RegistrationResponse] = []
