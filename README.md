# APAAR NEXUS
### AICTE Student Data Management & Verification Platform *(academic / SIH prototype)*

> **Prototype notice.** This project uses **synthetic data only**. It is **not** connected to AICTE
> production systems, the government APAAR database, Aadhaar, DigiLocker, or any state or government
> verification API. APAAR-ID checks are **format validation only**, and the OTP step is a **simulation**.

**Status: work in progress.** See [`docs/PROGRESS.md`](docs/PROGRESS.md) for exactly what is built,
what is tested and what is still to do. This README only describes what exists today.

## What exists today
- FastAPI backend with a 33-table data model (persons separate from enrolments, dynamic vault
  document types, audit/security tables, duplicate cases, bulk imports).
- Authentication: Argon2id passwords, short-lived JWT access tokens, rotating refresh tokens with
  reuse detection, account lockout, rate limiting, password change/reset.
- Role-based access control (6 roles) enforced in backend dependencies, with institution/state scoping
  helpers and privilege-escalation guards.
- Users API, audit logging (append-only writer) and security-event detection.
- Alembic migration, Docker/Compose config (not yet run), CI workflow (backend).

## Local development (backend, no Docker)
```bash
cd backend
uv sync
cp ../.env.example .env        # then set DATABASE_URL=sqlite:///./apaar_nexus.db for a quick start
uv run alembic upgrade head
uv run python -m app.seed      # synthetic demo data
uv run uvicorn app.main:app --reload   # http://localhost:8000/docs
uv run pytest -q
uv run ruff check app tests
```

## Demo accounts (development only, synthetic)
All demo users share the password `Demo@12345!` (seeded only when `ENVIRONMENT != production`).

| Username | Role |
|---|---|
| `superadmin` | Super Admin |
| `aicte.admin` | AICTE Admin |
| `state.mh` | State Admin (Maharashtra) |
| `inst.admin.pune`, `inst.admin.nagpur` | Institution Admin |
| `inst.staff.pune`, `inst.staff.nagpur` | Institution Staff |
| `verifier.1` | Verification Officer |

The app refuses to start in production if `DEMO_MODE`/`EXPOSE_DEMO_OTP` are on or `SECRET_KEY` is weak.

## Roles (summary)
Super Admin · AICTE Admin · State Admin · Institution Admin · Institution Staff · Verification Officer.
The permission matrix lives in `backend/app/core/permissions.py` and is seeded into the database.

## Known limitations (current)
- No frontend yet. No PostgreSQL or Docker verification yet. Most domain modules are still to come.
