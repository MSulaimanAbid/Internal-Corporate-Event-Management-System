# Internal Corporate Event Management System

A REST API built with **FastAPI** and **PostgreSQL** that lets Acme Corp employees browse and register for internal corporate events, while giving admins full control to create, update, and remove them.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Architecture Overview](#architecture-overview)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Running the Server](#running-the-server)
- [Interactive API Docs](#interactive-api-docs)
- [Business Rules](#business-rules)
- [Request & Response Shapes](#request--response-shapes)
- [Error Reference](#error-reference)

---

## Features

- **Create, read, update, delete events** — full CRUD for corporate events
- **Search & filter events** — filter by partial title (case-insensitive) and/or exact date
- **Paginated event listing** — `skip` / `limit` query parameters for page navigation
- **Employee registration** — register for any event using an email address
- **Capacity enforcement** — registrations are blocked once an event reaches `max_capacity`
- **Duplicate prevention** — an employee cannot register for the same event twice
- **Cascade deletion** — deleting an event automatically removes all its registrations
- **Auto-generated API docs** — interactive Swagger UI at `/docs` out of the box

---

## Tech Stack

| Layer         | Technology                                  |
|---------------|---------------------------------------------|
| Web framework | [FastAPI](https://fastapi.tiangolo.com/)    |
| ASGI server   | [Uvicorn](https://www.uvicorn.org/)         |
| ORM           | [SQLAlchemy](https://www.sqlalchemy.org/)   |
| Validation    | [Pydantic v2](https://docs.pydantic.dev/)   |
| Database      | PostgreSQL                                  |
| DB driver     | psycopg2-binary                             |
| Config        | python-dotenv (`.env` file)                 |
| Testing       | pytest                                      |
| Auth (future) | python-jose (JWT) · passlib (hashing)       |

---

## Project Structure

```
Internal-Corporate-Event-Management-System/
├── main.py          # FastAPI app instance + all HTTP route handlers
├── services.py      # Business logic layer — all DB queries live here
├── models.py        # SQLAlchemy ORM models (Event, Registration tables)
├── schemas.py       # Pydantic request / response schemas & validation rules
├── db.py            # DB engine, session factory, get_db dependency
├── requirements.txt # Python dependencies
├── .env             # Secrets (DB URL) — gitignored, never committed
└── .gitignore
```

---

## Architecture Overview

The application follows a clean **three-layer architecture** so each file has a single, well-defined responsibility:

```
HTTP Request
     │
     ▼
┌─────────────┐
│   main.py   │  ← Route handlers: validate input, call services, return responses
└──────┬──────┘
       │ calls
       ▼
┌──────────────┐
│  services.py │  ← Business logic: DB queries, capacity checks, duplicate guards
└──────┬───────┘
       │ queries
       ▼
┌──────────────┐
│   models.py  │  ← SQLAlchemy ORM models mapped to PostgreSQL tables
└──────┬───────┘
       │ backed by
       ▼
┌──────────────┐
│    db.py     │  ← Engine, SessionLocal, get_db() dependency
└──────────────┘

schemas.py sits alongside main.py — it validates all incoming request bodies
and shapes all outgoing response bodies (Pydantic V2).
```

**Key design principles:**
- Routes are **thin** — one or two lines that delegate to a service function.
- Services **never** import FastAPI or raise `HTTPException` — they return `None` or sentinel strings (`"CAPACITY_REACHED"`, `"DUPLICATE"`), and the route translates these into the right HTTP status codes.
- DB sessions are managed exclusively by `get_db()` in `db.py` via FastAPI's `Depends()` — services never open their own sessions.

---

## Database Schema

### `events` table

| Column         | Type    | Constraints                         |
|----------------|---------|-------------------------------------|
| `id`           | INTEGER | Primary Key, auto-increment, index  |
| `title`        | VARCHAR | NOT NULL                            |
| `description`  | VARCHAR | NOT NULL                            |
| `date`         | DATE    | NOT NULL                            |
| `location`     | VARCHAR | NOT NULL                            |
| `max_capacity` | INTEGER | NOT NULL                            |

### `registrations` table

| Column           | Type    | Constraints                           |
|------------------|---------|---------------------------------------|
| `id`             | INTEGER | Primary Key, auto-increment           |
| `employee_email` | VARCHAR | NOT NULL, index                       |
| `event_id`       | INTEGER | NOT NULL, Foreign Key → `events.id`   |

**Unique constraint:** `(employee_email, event_id)` — prevents duplicate registrations.  
**Cascade:** Deleting an `Event` automatically deletes all its `Registration` rows.

---

## API Endpoints

### Events

| Method   | Path           | Description                                            | Status codes  |
|----------|----------------|--------------------------------------------------------|---------------|
| `POST`   | `/events`      | Create a new event                                     | 201, 422      |
| `GET`    | `/events`      | List events (paginated; optional title & date filters) | 200           |
| `GET`    | `/events/{id}` | Get a single event by id                               | 200, 404      |
| `PUT`    | `/events/{id}` | Partially update an event (only send changed fields)   | 200, 404, 422 |
| `DELETE` | `/events/{id}` | Delete an event and all its registrations              | 204, 404      |

### Registrations

| Method   | Path                         | Description                         | Status codes       |
|----------|------------------------------|-------------------------------------|--------------------|
| `POST`   | `/events/{id}/registrations` | Register an employee for an event   | 201, 404, 409, 422 |
| `GET`    | `/events/{id}/registrations` | List all registrations for an event | 200, 404           |
| `DELETE` | `/registrations/{id}`        | Cancel a registration by its id     | 204, 404           |

#### Query parameters for `GET /events`

| Parameter | Type   | Default | Description                                                       |
|-----------|--------|---------|-------------------------------------------------------------------|
| `skip`    | int    | `0`     | Number of records to skip (for pagination)                        |
| `limit`   | int    | `10`    | Maximum records to return                                         |
| `title`   | string | —       | Case-insensitive partial match on event title (e.g. `?title=py`) |
| `date`    | date   | —       | Exact date filter in `YYYY-MM-DD` format (e.g. `?date=2025-06-15`)|

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL running locally or remotely
- A database already created (e.g. `event_db`)

### 1 — Clone the repo

```bash
git clone <your-repo-url>
cd Internal-Corporate-Event-Management-System
```

### 2 — Create and activate a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### 4 — Configure environment variables

Create a `.env` file in the project root (it is gitignored):

```env
SQL_URL=postgresql://username:password@localhost:5432/event_db
```

Replace `username`, `password`, and `event_db` with your actual PostgreSQL credentials and database name.

### 5 — Create the database tables

The tables are created automatically on server startup. To provision them without starting the server, run:

```bash
python db.py
# Tables created successfully.
```

---

## Environment Variables

| Variable  | Required | Description                       |
|-----------|----------|-----------------------------------|
| `SQL_URL` | ✅ Yes   | Full PostgreSQL connection string |

**Format:** `postgresql://user:password@host:port/dbname`

---

## Running the Server

```bash
uvicorn main:app --reload
```

| Flag       | Purpose                                          |
|------------|--------------------------------------------------|
| `--reload` | Auto-restart on file changes (development only)  |

The server starts at **`http://127.0.0.1:8000`** by default.

To bind to a different host/port:

```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

---

## Interactive API Docs

FastAPI generates interactive documentation automatically:

| URL                                  | Interface            |
|--------------------------------------|----------------------|
| `http://127.0.0.1:8000/docs`         | Swagger UI           |
| `http://127.0.0.1:8000/redoc`        | ReDoc                |
| `http://127.0.0.1:8000/openapi.json` | Raw OpenAPI schema   |

---

## Business Rules

1. **Event must exist** — Registering for or viewing registrations of a non-existent event returns `404 Not Found`.
2. **Capacity check** — If the number of existing registrations equals `max_capacity`, new registrations return `409 Conflict` with `"Event capacity reached"`.
3. **Duplicate check** — If the same `employee_email` tries to register for the same event twice, the response is `409 Conflict` with `"Employee already registered for this event"`. This is checked in the service layer _before_ hitting the DB-level unique constraint.
4. **Cascade delete** — Deleting an event removes all associated registrations in the same transaction; no orphan rows are left behind.
5. **Partial updates** — `PUT /events/{id}` accepts any subset of event fields; only the provided fields are written to the database (unset fields are ignored via `exclude_unset=True`).

---

## Request & Response Shapes

### Create Event — `POST /events`

**Request body:**
```json
{
  "title": "Python Workshop",
  "description": "Hands-on intro to FastAPI and SQLAlchemy.",
  "date": "2025-06-15",
  "location": "Conference Room B",
  "max_capacity": 30
}
```

**Response `201`:**
```json
{
  "id": 1,
  "title": "Python Workshop",
  "description": "Hands-on intro to FastAPI and SQLAlchemy.",
  "date": "2025-06-15",
  "location": "Conference Room B",
  "max_capacity": 30
}
```

---

### Update an Event — `PUT /events/{id}`

Send only the fields you want to change — all fields are optional:

```json
{
  "location": "Main Auditorium",
  "max_capacity": 50
}
```

---

### Register for an Event — `POST /events/{id}/registrations`

**Request body:**
```json
{
  "employee_email": "jane.doe@acmecorp.com"
}
```

**Response `201`:**
```json
{
  "id": 42,
  "employee_email": "jane.doe@acmecorp.com",
  "event_id": 1
}
```

---

## Error Reference

| Status | Meaning              | When it happens                                                            |
|--------|----------------------|----------------------------------------------------------------------------|
| `201`  | Created              | Event or registration successfully created                                 |
| `204`  | No Content           | Event or registration successfully deleted                                 |
| `404`  | Not Found            | No event or registration exists with the given `id`                        |
| `409`  | Conflict             | Event is at full capacity, or employee has already registered              |
| `422`  | Unprocessable Entity | Request body failed Pydantic validation (missing field, wrong type, etc.)  |
