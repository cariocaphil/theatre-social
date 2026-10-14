# Agent instructions — Theatre Social

Persistent, tool-agnostic instructions for coding agents working in this repository.

For product purpose, setup, and feature details, prefer the linked docs over
duplicating them here.

## Project context

Theatre Social (also referred to as **Crummles**) is a theatre-focused social
product. Users browse a catalogue of **Productions** (specific stagings/runs) and
can log attendances as private **DiaryEntry** records with optional ratings and
reviews.

**Stack (as implemented):**

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 15 (App Router, TypeScript), pnpm, Vitest |
| Backend | FastAPI, SQLAlchemy 2 (async) + asyncpg, Alembic, uv, Ruff, pytest |
| Database | PostgreSQL 16 |
| Local orchestration | OCI Compose (`compose.yml`) — Podman or Docker |
| CI/CD | GitHub Actions (`.github/workflows/ci.yml`) |
| Production | Azure Container Apps + Azure Database for PostgreSQL Flexible Server |

**Read first:**

- [README.md](README.md) — setup, features, CI, production deployment
- [docs/architecture.md](docs/architecture.md) — current system architecture
- [docs/roadmap.md](docs/roadmap.md) — completed phases and proposed next work
- [docs/decisions/README.md](docs/decisions/README.md) — when and how to record ADRs

## Architecture conventions

### Layout

- `frontend/` — App Router pages under `app/`, interactive UI in `components/`,
  typed API clients in `lib/`
- `backend/app/` — `api/routes` (HTTP), `schemas` (Pydantic DTOs), `services`
  (business logic), `models` (SQLAlchemy ORM), `db` (engine/session/seed),
  `core` (config, security, shared helpers)

### Backend request flow

Routes stay thin: validate via Pydantic schemas, call a service, map domain
exceptions to HTTP status codes. Services own queries, ownership rules, and
transactions. Models are persistence only — no business logic in ORM classes.

### Domain conventions

- Domain entities that need identity + audit timestamps subclass
  `UUIDAuditBase` (`id`, `created_at`, `updated_at`).
- `Production` is the catalogue entity. Work/venue/company/person are **not**
  separate tables yet — they are optional text fields on `Production`.
- `DiaryEntry` is one attendance of a `Production` by a `User`. Multiple
  entries for the same `(user_id, production_id)` are allowed and expected.
- Schema changes go through Alembic migrations under `backend/alembic/versions/`.
  Do not rely on `create_all` outside tests.

### Auth boundaries

- Server-side sessions via an HTTP-only cookie (`ts_session` by default).
- Raw token in the cookie; SHA-256 hash in `sessions.token_hash`. Passwords use
  Argon2id. There is no `SESSION_SECRET_KEY`.
- Authenticated routes use `get_current_user` (`app/api/deps.py`). Diary
  `user_id` always comes from the session, never from the client body.
- Ownership misses return `404` (not `403`) where that pattern already exists.

### Frontend data fetching

- Server Components use `INTERNAL_API_URL` for catalogue/health fetches.
- Browser/client code uses `NEXT_PUBLIC_API_URL` (build-time inlined) with
  `credentials: "include"` for auth/diary.
- API helpers return `{ ok: true, data }` / `{ ok: false, error }` — avoid
  throwing for expected failure modes.

## Specification-driven development

For substantial changes:

1. Inspect the existing implementation and relevant docs.
2. Understand requested behavior, constraints, and dependencies.
3. Define scope, non-goals, and acceptance criteria.
4. Identify affected components and propose an approach.
5. Implement only the approved scope.
6. Add or update relevant tests.
7. Run appropriate verification commands.
8. Report changes, results, deviations, and remaining risks.

For substantial architectural changes, present the proposed approach **before**
implementation unless the user explicitly asks to execute immediately.

Avoid speculative abstractions, unnecessary dependencies, and unrelated
refactoring.

## Testing and verification

**Backend** (from `backend/`, requires reachable Postgres at `DATABASE_URL`):

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

**Frontend** (from `frontend/`):

```bash
pnpm lint
pnpm typecheck
pnpm format:check
pnpm test
pnpm build
```

- Behavioral changes need relevant regression tests.
- Match existing formatting/lint/typecheck conventions; do not weaken checks.
- Never claim checks passed unless they were actually run successfully.
- If a check could not be run, say so and why.

## Git discipline

- Branch naming in this repo: `feature/N-description`, `docs/N-description`,
  `fix/...` (see existing branches).
- Commit messages are short imperative summaries (`add …`, `fix: …`, `ci: …`,
  `chore: …`). Prefer coherent, logically separated commits.
- Keep changes focused and reviewable. Do not mix unrelated refactoring into a
  feature.
- **Do not** commit, push, force-push, rebase, or open PRs without explicit
  authorization.
- Never modify unrelated user changes.

## Security

- Do not expose secrets or credentials; never commit real `.env` values.
- Preserve authentication and authorization boundaries.
- Do not weaken security checks to make tests pass.
- Treat external/client input as untrusted; validate at the schema layer.
- Respect database integrity constraints and existing domain invariants
  (e.g. diary → production `ON DELETE RESTRICT`).

## Implementation reports

End substantial work with a concise report covering:

1. Files changed (and why, briefly).
2. Architectural decisions and tradeoffs.
3. Tests and checks executed (or not run, with reason).
4. Deviations from the specification.
5. Known limitations or remaining risks.
