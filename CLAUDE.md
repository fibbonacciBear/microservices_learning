# CLAUDE.md

## Project Overview

This repository is a staged microservices learning project built around a "Pizza Shop" domain.

Current implementation status:
- Phase 1 is implemented in `monolith/`.
- Later phases (decomposition, Kubernetes, observability, polyglot rewrite) are planned in `microservices_learning_project_774f51f8.plan.md` but are not implemented yet.

The Phase 1 app is a FastAPI monolith with:
- one process
- one SQLite database
- four domains: menu, orders, kitchen, notifications
- one static browser UI served by the same FastAPI app

## Working Directory

Most application work currently happens in:
- `monolith/`

Important files:
- `monolith/main.py`: FastAPI app wiring and startup
- `monolith/database.py`: SQLAlchemy engine, session factory, `Base`, `get_db`
- `monolith/models.py`: ORM models for all Phase 1 tables
- `monolith/schemas.py`: request/response models
- `monolith/seed.py`: startup seed data
- `monolith/routers/`: API route modules
- `monolith/static/`: browser UI assets
- `microservices_learning_project_774f51f8.plan.md`: long-term project plan

## Commands

Install dependencies:

```bash
cd monolith
pip install -r requirements.txt
```

Run the app locally:

```bash
cd monolith
uvicorn main:app --reload --port 8000
```

Useful URLs:
- UI: `http://localhost:8000/`
- Swagger: `http://localhost:8000/docs`

Quick syntax check:

```bash
python3 -m compileall monolith
```

Quick smoke test pattern:

```bash
python3 -c "import sys; sys.path.insert(0, 'monolith'); from fastapi.testclient import TestClient; import main; \
with TestClient(main.app) as client: \
    print(client.get('/menu').status_code)"
```

## Phase 1 Architecture Notes

- The SQLite database file lives at `monolith/pizza_shop.db`.
- Tables are created on FastAPI startup.
- Menu items are seeded on startup if the menu is empty.
- Static UI is mounted at `/`, so API routes need to be registered explicitly and should not rely on accidental redirect behavior.
- Root routes on prefixed routers should use `""`, not `"/"`, to avoid falling through to the static file mount.
- The kitchen cooking endpoint intentionally uses `time.sleep(5)` inside an `async def` handler. This is deliberate for the learning goal; do not "fix" it unless asked.

## Development Conventions

- Prefer targeted changes inside `monolith/` unless the user explicitly asks for later phases.
- Preserve the Phase 1 learning intent:
  - monolith first
  - shared database
  - deliberately coupled UI/backend
  - deliberately blocking kitchen simulation
- Keep API contracts stable unless the user asks to change them.
- If you add new endpoints, update both the router and the UI if the feature is user-facing.
- If you change data shape, update:
  - `models.py`
  - `schemas.py`
  - affected router(s)
  - `static/app.js`
- Treat `monolith/pizza_shop.db` as generated runtime state, not source code.
- Do not edit `__pycache__/` artifacts.

## Testing Guidance

For Phase 1 changes, prefer lightweight verification:
- `python3 -m compileall monolith`
- FastAPI `TestClient` smoke tests for modified endpoints

If a change affects the browser flow, verify at least the relevant backend path and mention if no manual browser test was run.

## Future Phases

The plan file describes future work, but none of these directories exist yet:
- `microservices/`
- `k8s/`
- C# service directories

Do not assume those phases are already scaffolded. Create them only if explicitly asked.
