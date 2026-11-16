"""
models.py — SQLAlchemy ORM Models

This module defines the database schema for the Internal Corporate Event
Management System using SQLAlchemy's declarative ORM layer.

Two tables are modelled here:
  - `events`        — stores corporate event details (title, date, capacity …)
  - `registrations` — stores which employee registered for which event

The relationship between them is one-to-many:
    Event (1) ──────< Registration (many)

Both classes inherit from `base` (defined in db.py) so SQLAlchemy can track
them when `create_tables()` is called.
"""

from sqlalchemy import Column, Date, ForeignKey, Integer, String, unique_constraint
from sqlalchemy.orm import relationship

# `base` is the declarative base from db.py — all models must inherit from it
# so SQLAlchemy registers their table definitions.
from db import base


class Event(base):
    """
    ORM model for the `events` table.

    Represents a single corporate event that employees can register for.

    Columns:
        id           (int, PK)  — Auto-incremented primary key; indexed for fast lookups.
        title        (str)      — Short, human-readable name of the event.
        description  (str)      — Longer text explaining the event's purpose/agenda.
        date         (date)     — Calendar date on which the event takes place.
        location     (str)      — Venue or virtual meeting link.
        max_capacity (int)      — Maximum number of attendees allowed; used to enforce limits.

    Relationships:
        Registrations — back-reference to all Registration rows linked to this event.
                        cascade="all, delete-orphan" means deleting an Event also
                        deletes all its Registration rows, keeping the DB consistent.

    Why we need it:
        Provides a structured, type-safe representation of an event that SQLAlchemy
        maps to/from the PostgreSQL `events` table automatically.
    """

    __tablename__ = "events"  # The actual table name in PostgreSQL

    # Primary key — auto-incremented by the DB; indexed for O(1) lookups by id.
    id = Column(Integer, primary_key=True, index=True)

    # Core event fields — all required (nullable=False enforced at DB level).
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    location = Column(String, nullable=False)
    max_capacity = Column(Integer, nullable=False)

    # One-to-many relationship: one Event → many Registrations.
    # `cascade="all, delete-orphan"` ensures child registrations are removed
    # automatically when the parent event is deleted.
    Registrations = relationship(
        "Registration", back_populates="event", cascade="all, delete-orphan"
    )


class Registration(base):
    """
    ORM model for the `registrations` table.

    Records that a specific employee (identified by email) has registered for
    a specific event.

    Columns:
        id             (int, PK)  — Auto-incremented primary key.
        employee_email (str)      — Email of the registering employee; indexed for
                                    fast lookups (e.g., "find all events for user X").
        event_id       (int, FK)  — Foreign key to `events.id`; links the registration
                                    to its parent event.

    Constraints:
        employee_event_unique — A composite UNIQUE constraint on (employee_email, event_id)
                                so the same employee cannot register for the same event twice.

    Relationships:
        event — back-reference to the parent Event object.

    Why we need it:
        Cleanly enforces the many-to-many join between employees and events at the
        database level, with a uniqueness guard to prevent duplicate registrations.
    """

    __tablename__ = "registrations"  # The actual table name in PostgreSQL

    # Primary key — auto-incremented.
    id = Column(Integer, primary_key=True, index=True)

    # The employee's email address; indexed because we'll frequently query
    # "all registrations for this employee".
    employee_email = Column(String, nullable=False, index=True)

    # Foreign key linking this registration to a specific event.
    # If the event is deleted, this row is also deleted (via cascade on Event).
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)

    # Many-to-one back-reference: each Registration belongs to one Event.
    event = relationship("Event", back_populates="Registrations")

    # Table-level constraints defined here because SQLAlchemy requires them in
    # __table_args__ when they span multiple columns.
    __table_args__ = (
        # Prevents an employee from registering for the same event more than once.
        unique_constraint("employee_email", "event_id", name="employee_event_unique"),
    )
