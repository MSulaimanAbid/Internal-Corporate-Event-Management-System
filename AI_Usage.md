# AI Usage Log — Internal Corporate Event Management System

This file documents every AI-assisted interaction during the development of this project:
the tool used, the model, and each prompt in chronological order.

---

## AI Tool & Model

| Field      | Detail                                                                 |
|------------|------------------------------------------------------------------------|
| **Tool**   | [Antigravity](https://antigravity.dev) — AI coding assistant by Google DeepMind |
| **Model**  | Claude Sonnet 4.6 (Thinking) by Anthropic                             |
| **Mode**   | Inline coding assistant inside the Antigravity IDE                    |

> [!NOTE]
> The model was switched to **Claude Sonnet 4.6 (Thinking)** at the start of the first
> coding session (2026-11-16). All interactions listed below ran on this model.

---

## Prompt Log

---

### Prompt 1 — Project Kickoff
**Date:** 2026-11-16  
**Purpose:** Understand the project scope and get a structured plan before writing any code.

> *"this is my project document i want you to explain in detailed what is project about and give me the roadmap of the project and also make one file that contain the tasks which will be done in the project building"*

**What the AI did:**
- Read the project document and explained the full scope of the Internal Corporate Event Management System.
- Produced a detailed project roadmap covering setup, models, schemas, services, routes, auth, and testing phases.
- Created a task-tracking file outlining all work to be done.

---

### Prompt 2 — Add Comments & Docstrings (db.py, models.py) + Create claude.md
**Date:** 2026-11-16  
**Files affected:** `db.py`, `models.py`, `.gitignore`, `claude.md` *(created)*  
**Purpose:** Document existing code with inline comments and docstrings; set up persistent AI memory.

> *"add comments explaining what is being done and why inline with the code and concise and easy to understand*
>
> *add a docstring always on each file to explain what is going on*
>
> *for each function add a docstring and mention expected input, outputs and a short explanation what that function does and why we need it*
>
> *donot change any code unless i ask you to or I approve*
>
> *add all this to your memory and keep all memory of this project here in the repo inside claude.md make sure gitignore it"*

**What the AI did:**
- Added a module-level docstring to `db.py` and `models.py`.
- Added full docstrings (inputs / outputs / why) to `get_db()` and `create_tables()` in `db.py`.
- Added class docstrings and inline comments to `Event` and `Registration` in `models.py`.
- Created `claude.md` as the persistent project memory file (schema, conventions, change log).
- Added `claude.md` to `.gitignore`.

---

### Prompt 3 — Add Comments & Docstrings (schemas.py)
**Date:** 2026-11-16  
**Files affected:** `schemas.py`  
**Purpose:** Document all Pydantic schemas with the same standard — no code changes.

> *"now add comments in the schemas.py and dont change any code just add comments"*

**What the AI did:**
- Added a module-level docstring explaining the schema hierarchy as a tree diagram.
- Added or upgraded docstrings on all 7 classes: `EventBase`, `EventCreate`, `EventUpdate`, `EventResponse`, `RegistrationBase`, `RegistrationCreate`, `RegistrationResponse`, `EventWithRegistrationsResponse`.
- Added inline comments on every field explaining its validation rule (`...` = required, `min_length`, `gt=0`, `EmailStr`, `from_attributes=True`).
- Zero code changed.

---

### Prompt 4 — Add Comments & Docstrings (services.py, main.py) — First Pass
**Date:** 2026-11-17  
**Files affected:** `services.py`, `main.py`  
**Purpose:** Document the business logic layer and route handlers — no code changes.

> *"add comments in services.py and main.py and do not change the code just add comments"*

**What the AI did:**
- Added module docstrings to both files.
- Added full docstrings + inline comments to all functions in `services.py`: `get_events`, `get_event`, `create_event`, `update_event`, `delete_event`.
- Added full docstrings + inline comments to all route handlers in `main.py`: `create_event`, `read_events`, `read_event`, `update_event`, `delete_event`.
- Zero code changed.

---

### Prompt 5 — Add Comments on Newly Added Code (services.py, main.py)
**Date:** 2026-11-17  
**Files affected:** `services.py`, `main.py`  
**Purpose:** The user had added new functions and routes since the last session — document them.

> *"i have updated the services.py and main.py add comments on that too and do not change the code just add comments"*

**What the AI did:**
- Added docstrings + inline comments to 3 new service functions: `create_registration` (including explanation of the 3-rule sentinel pattern), `get_event_registrations`, `delete_registration`.
- Added docstrings + inline comments to 3 new route handlers: `register_for_event`, `view_event_registrations`, `cancel_registration`.
- Updated the module docstring in `main.py` to list the new registration endpoints.
- Updated `claude.md` change log.
- Zero code changed.

---

### Prompt 6 — Verify claude.md is Gitignored
**Date:** 2026-11-17  
**Files affected:** `.gitignore`  
**Purpose:** Confirm the memory file would not be committed to the repository.

> *"is claude.md in the .gitignore"*

**What the AI did:**
- Searched `.gitignore` for the `claude.md` entry.
- Found it was missing (lost due to a server restart between sessions).
- Re-added the entry at the bottom of `.gitignore` and verified it with a second search.

---

### Prompt 7 — Add Comments on Updated Code (services.py, main.py) + Update claude.md
**Date:** 2026-11-17  
**Files affected:** `services.py`, `main.py`, `claude.md`  
**Purpose:** The user had again updated both files with new features (title/date filtering). Document the changes.

> *"now add the comments in the services.py and main.py and do not change the code and also update the claude.md file"*

**What the AI did:**
- Added a full docstring to the updated `get_events()` in `services.py` (now supports `title` and `event_date` filter params).
- Upgraded inline comments inside `get_events()` to explain the `ilike` wildcard pattern and exact-date filter.
- Added a full docstring to the updated `read_events()` in `main.py` (now has `title` and `date` as optional query params).
- Added an inline comment to the stray `from datetime import date as date_type` import that appeared mid-file.
- Updated `claude.md`: marked `schemas.py`, `services.py`, and `main.py` as complete in the open-work checklist; added a change log entry.
- Zero code changed.

---

### Prompt 8 — Write README.md
**Date:** 2026-11-17  
**Files affected:** `README.md`  
**Purpose:** Create a comprehensive project README for anyone reading the repository.

> *"now make a readme.md file that explain all the details about the project"*

**What the AI did:**
- Replaced the placeholder `README.md` with a full document covering:
  - Feature list
  - Tech stack table
  - Project file structure
  - Architecture overview (ASCII diagram + design principles)
  - Database schema tables
  - Full API endpoint reference with query parameters
  - Step-by-step getting started guide (clone → venv → install → `.env` → run)
  - Environment variable reference
  - Business rules (5 rules in plain English)
  - Request/response JSON examples
  - HTTP error reference table

---

### Prompt 9 — Explain services.py
**Date:** 2026-11-17  
**Purpose:** Understand the role and internals of the business logic layer.

> *"explain what is in service.py what is usage of this file"*

**What the AI did:**
- Explained services.py as the "brain" of the application — the only place where DB queries run and business rules are enforced.
- Showed the three-layer architecture diagram placing services.py between routes and models.
- Described every function (purpose, inputs, outputs).
- Detailed the 3-rule guard sequence inside `create_registration` (event exists → capacity check → duplicate check).
- Explained the sentinel string pattern (`None`, `"CAPACITY_REACHED"`, `"DUPLICATE"`) and why it keeps the service layer decoupled from FastAPI/HTTP.

---

### Prompt 10 — Create AI_Usage.md *(this file)*
**Date:** 2026-11-18  
**Files affected:** `AI_Usage.md` *(created)*  
**Purpose:** Log all AI interactions on this project for transparency and learning reference.

> *"now i want you to make AI_Usage.md file which contain all the prompts related to this project and this prompt 'this is my project document i want you to explain in detailed what is project about and give me the roadmap of the project and also make one file that contain the tasks which will be done in the project building' this prompt will be the first prompt i use and also i want you to add which AI tool i used and which model"*

**What the AI did:**
- Read the full conversation transcript to retrieve exact prompts and timestamps.
- Created this `AI_Usage.md` file documenting all 10 prompts in chronological order with context, purpose, and outcome for each.

---

## Summary

| # | Date       | Prompt Topic                                              | Files Changed                          |
|---|------------|-----------------------------------------------------------|----------------------------------------|
| 1 | 2026-11-16 | Project kickoff — explanation + roadmap + task file       | *(pre-codebase)*                       |
| 2 | 2026-11-16 | Comments + docstrings for `db.py` & `models.py`           | `db.py`, `models.py`, `claude.md`, `.gitignore` |
| 3 | 2026-11-16 | Comments + docstrings for `schemas.py`                    | `schemas.py`                           |
| 4 | 2026-11-17 | Comments + docstrings for `services.py` & `main.py`       | `services.py`, `main.py`              |
| 5 | 2026-11-17 | Comments on newly added registration functions & routes   | `services.py`, `main.py`              |
| 6 | 2026-11-17 | Verify `claude.md` is gitignored                          | `.gitignore`                           |
| 7 | 2026-11-17 | Comments on updated filtering code + update `claude.md`   | `services.py`, `main.py`, `claude.md` |
| 8 | 2026-11-17 | Write full `README.md`                                    | `README.md`                            |
| 9 | 2026-11-17 | Explain `services.py`                                     | *(explanation only, no files)*         |
| 10| 2026-11-18 | Create this `AI_Usage.md` file                            | `AI_Usage.md`                          |
