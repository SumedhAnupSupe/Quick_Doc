# Implementation progress

Legend: ✅ done & tested · 🟡 written, not yet runnable end-to-end · ⬜ not started

Last verified: backend `ruff` clean, `pytest` 25 passed (SQLite), Alembic upgrade/check/downgrade on SQLite.
**Not verified yet:** anything on PostgreSQL, Docker build/compose, frontend (does not exist yet), Playwright.

## Milestone 1 - Foundation
- ✅ Backend skeleton (FastAPI, SQLAlchemy 2, Alembic, uv), ruff config, config/env handling
- 🟡 Dockerfile + docker-compose (db + isolated vault DBs + backend) - written, **not built/run**
- ✅ `.env.example`, `.gitignore`
- 🟡 CI workflow (backend only so far) - not yet run on GitHub
- ⬜ Frontend scaffold, frontend CI job

## Milestone 2 - Database
- ✅ 33 tables as SQLAlchemy models (persons/enrolments split, dynamic document types, audit, OTP, imports...)
- ✅ Initial Alembic migration (verified on SQLite: upgrade, no drift, downgrade)
- ✅ RBAC + minimal demo seed (roles, permissions, institution types, seat categories, 3 institutions, 8 users)
- ⬜ Rich demo seed (students, enrolments, documents, duplicates, intakes, audit/security events)
- ⬜ Verify migration on PostgreSQL

## Milestone 3 - Authentication & authorization
- ✅ Login/logout, Argon2id, JWT access + rotating refresh tokens with reuse detection
- ✅ Lockout, rate limit, password policy/change/reset, `/auth/me`
- ✅ RBAC dependencies, institution/state scope helpers, escalation guards
- ✅ Users API (list/create/get/update/status/roles) with scoping + tests

## Milestones 4-12
- ⬜ 4 Institutions & academics  - ⬜ 5 Persons & enrolments  - ⬜ 6 Vaults & documents
- ⬜ 7 Verification & duplicates (+OTP simulation)  - ⬜ 8 Bulk import & reports
- ⬜ 9 Frontend (landing, login, shell, all screens)  - ⬜ 10 Audit/security APIs & monitoring screens
- ⬜ 11 Full test pass (frontend, Playwright, Docker)  - ⬜ 12 Docs & release prep

## Known weak spots to revisit
- `test_audit_log_has_no_mutation_endpoints` currently passes only because no audit route exists yet;
  strengthen it once `/audit-logs` (GET) is implemented.
- Staff roles lack `user:read`, so they cannot yet edit their own profile; add a `/auth/me` PATCH.
- In-process rate limiter is per-instance (fine for a prototype; use Redis if scaled out).
