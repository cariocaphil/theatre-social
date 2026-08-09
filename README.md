# Theatre Social

Monorepo foundation for Theatre Social: a Next.js (TypeScript, App Router) frontend, a
FastAPI (Python, async SQLAlchemy 2 + `asyncpg`) backend, and PostgreSQL, orchestrated
with an OCI-compatible Compose file that works with rootless Podman or Docker.

Phase 1 built the **foundation**: project scaffolding, a `/health` endpoint that
verifies database connectivity end-to-end, and the container / migration / testing
setup needed to build real features on top of it.

Phase 2 (v0.1) adds the first real domain feature: a read-only **Production
catalogue** (see [Production Catalogue (v0.1)](#production-catalogue-v01) below).
There is still no authentication, user accounts, reviews, ratings, or diary
functionality.

Phase 3 adds **Continuous Integration**: every push and pull request to `main` is
automatically linted, type-checked, tested, and built on GitHub Actions (see
[Continuous Integration](#continuous-integration) below). This phase is CI only —
there is no deployment, image publishing, or external SaaS integration.

Phase 4 adds minimal **Users & Authentication**: registration, login, logout, and a
`/me` account summary, backed by a server-side session stored in an HTTP-only cookie
(see [Users & Authentication](#users--authentication) below). There is still no
Production logging, diary, ratings, reviews, follows, or public profiles.

```
theatre-social/
├── frontend/     Next.js (TypeScript, App Router), pnpm
├── backend/      FastAPI, SQLAlchemy 2 (async), Alembic, uv
├── compose.yml   Postgres + backend + frontend orchestration
├── .env.example  Compose-level environment variables
└── README.md
```

## Prerequisites

- **Podman** ≥ 4.x with a running rootless machine (tested with Podman 6.0.2 on macOS,
  `applehv` machine). Docker Desktop / Docker Engine with Compose v2 also works as a
  drop-in replacement for every `podman` command below.
- **podman-compose** ≥ 1.0 (tested with 1.6.0), *or* Podman's built-in `podman compose`
  (Podman 4.7+), *or* `docker compose`.
- macOS/Windows only: a running Podman machine — `podman machine init && podman machine start`.
- Nothing else is required to run the stack: Node.js, pnpm, Python, and `uv` all run
  *inside* the containers. You only need them locally if you want to run tests/linting
  outside of containers (see [Local (non-container) development](#local-non-container-development)).

## 1. Configure environment variables

Copy the example env files. Defaults are sane for local development and contain no
real secrets.

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

- **`.env`** (root) — consumed by `compose.yml`: Postgres credentials, `DATABASE_URL`,
  `CORS_ORIGINS`, `INTERNAL_API_URL`, `NEXT_PUBLIC_API_URL`. This is what actually
  configures the containers.
- **`backend/.env`** / **`frontend/.env.local`** — only used if you run that app
  directly on the host, outside of Compose (see below). They use `localhost` instead
  of Compose service names, since the host can't resolve container DNS names.
- **`SESSION_COOKIE_NAME`** / **`SESSION_LIFETIME_DAYS`** (backend, optional) —
  configure the authentication session cookie; see
  [Users & Authentication](#users--authentication) below. Both have sensible defaults
  (`ts_session`, `30`) and are not present in `compose.yml` since the defaults are
  fine for local development — set them as real environment variables (not `.env`
  files, which aren't loaded in production-like deployments) if you need to override
  them.

## 2. Start the stack

```bash
podman compose up --build
```

If your Podman install doesn't have the built-in `compose` subcommand, use the
standalone tool instead (same flags):

```bash
podman-compose up --build
```

With Docker instead of Podman:

```bash
docker compose up --build
```

First boot takes longer (Postgres initialization, dependency installation, Next.js
compile). Once healthy, you'll see three containers running:

| Service    | Container port | Host port |
|------------|-----------------|-----------|
| `frontend` | 3000            | 3000      |
| `backend`  | 8000            | 8000      |
| `postgres` | 5432            | 5432      |

To run in the background: `podman compose up --build -d`.

## 3. Access the app

- **Frontend:** http://localhost:3000 — shows API reachability and database status,
  fetched server-side on load, with a "Check again" button for a client-side re-check.
- **Production catalogue:** http://localhost:3000/productions
- **Sign up / Log in:** http://localhost:3000/register / http://localhost:3000/login
- **Account summary:** http://localhost:3000/me
- **Backend health check:** http://localhost:8000/health
- **Production catalogue API:** http://localhost:8000/api/v1/productions
- **Auth API:** http://localhost:8000/api/v1/auth/{register,login,logout,me}
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI schema:** http://localhost:8000/openapi.json

### `backend:8000` vs `localhost:8000`

There are two different backend URLs used in this project, and they are **not**
interchangeable:

- `http://backend:8000` — only resolvable *inside* the Compose network. `backend` is
  the Compose service name, used when one container talks to another (e.g. the
  frontend's Node.js server fetching `/health` server-side). This is `INTERNAL_API_URL`.
- `http://localhost:8000` — the backend as seen from the **host machine** (your
  browser, `curl`, etc.), via the port Compose published to the host. This is
  `NEXT_PUBLIC_API_URL`, baked into the browser-side JavaScript bundle.

Using `localhost` inside a container would point at that container itself, not the
`backend` container — this is a common source of confusion, so the two URLs are kept
as separate, explicitly-named env vars throughout.

## Production Catalogue (v0.1)

> Production is the primary catalogue entity. Users will eventually log Productions.

A **Production** represents a specific staging that users will eventually be able to
log, review, rate, or discuss — e.g. a run of "Hamlet" at a specific theatre, a
stand-up set, an improv night, or a devised theatre piece.

### Why no separate Work / Venue entities yet

> Work and Venue are intentionally not separate entities in v0.1. Their values are
> stored as optional Production metadata until concrete product requirements justify
> normalization.

Modeling Works and Venues as their own tables would require deciding — before any
real usage data exists — whether Works need their own pages, whether Venues need
their own pages, how adaptations should be grouped under a Work, how touring
Productions relate to multiple Venues, and whether a Venue eventually belongs to a
Production or to an individual performance. v0.1 avoids answering those questions
prematurely by storing `work_title`, `venue_name`, `creator_names`, `company_name`,
and `director_name` as plain optional text columns directly on `productions`.

### Data model

`Production` inherits `id` (UUID, generated app-side), `created_at`, and `updated_at`
(both DB-generated via `server_default=func.now()`) from a shared `UUIDAuditBase` in
`app/db/base.py` — no per-model primary-key or timestamp logic is duplicated.

| Field | Required | Notes |
|---|---|---|
| `title` | Yes | Must not be blank. |
| `slug` | Yes (at persistence) | Auto-generated from `title` if omitted; unique at the database level. |
| `description` | No | Free text. |
| `work_title` | No | Underlying source-material title, if any. |
| `creator_names` | No | Free-text attribution (playwright, deviser, ensemble, ...). |
| `company_name` | No | Producing/performing company, plain text. |
| `director_name` | No | Plain text. |
| `venue_name` | No | Plain text. |
| `city` / `country_code` | No | `country_code` must be a 2-letter code when supplied. |
| `premiere_date` / `closing_date` | No | `closing_date` must be ≥ `premiere_date` when both are supplied. |

There is no status field, and lifecycle status (e.g. "running" / "closed") is never
inferred from dates in the database model — that logic, if ever needed, belongs in the
API or frontend layer, not persisted state.

### Slugs

> Slugs are stable public URL identifiers. Changing a Production title does not
> automatically change its slug.

- Omit `slug` on create and the backend generates one from `title` (lowercased,
  ASCII-transliterated where possible, non-alphanumeric runs collapsed to single
  hyphens).
- On collision, a deterministic numeric suffix is appended: `hamlet`, `hamlet-2`,
  `hamlet-3`, ... — never a random hash.
- The database's unique index on `slug` is the final source of truth for concurrency
  safety; an explicit duplicate slug on create/update returns `409 Conflict`.
- Updating `title` never touches `slug`. `slug` only changes when explicitly included
  in a `PATCH` request.

### REST API

```text
GET    /api/v1/productions            List (search/filter/paginate)
POST   /api/v1/productions            Create
GET    /api/v1/productions/{id}       Get by UUID
PATCH  /api/v1/productions/{id}       Partial update
DELETE /api/v1/productions/{id}       Delete
GET    /api/v1/productions/slug/{slug} Get by slug
```

`GET /api/v1/productions/slug/{slug}` is registered before `GET /api/v1/productions/{id}`
in `app/api/routes/productions.py`; since the two paths have a different number of
path segments, there is no real ambiguity, but the ordering is kept explicit for
clarity. `{id}` is typed as a UUID, so a malformed ID (including the literal string
`slug` with no further segment) fails FastAPI's path validation with `422`, not `404`.

Status codes: `200` (reads/updates), `201` (create), `204` (delete), `404` (missing
Production), `409` (duplicate explicit slug), `422` (validation errors, including
blank titles, invalid `country_code`, invalid date ranges, and malformed UUIDs).

#### List filtering parameters

`search`, `work_title`, `company_name`, `director_name`, `venue_name`, `city`,
`country_code`, `from_date`, `to_date`, `limit` (1–100, default 20), `offset` (≥ 0,
default 0).

- `search` matches (case-insensitively, via `ILIKE`) `title`, `work_title`,
  `creator_names`, `company_name`, `director_name`, `venue_name`, and `city`.
- `work_title`, `company_name`, `director_name`, `venue_name`, `city` are individual
  case-insensitive partial-match filters.
- `country_code` is an exact, case-insensitive match.

#### Date filtering semantics

A Production matches a date filter based on overlap between its known
`[premiere_date, closing_date]` range and the requested `[from_date, to_date]` range:

- **No `from_date`/`to_date` supplied:** no date filtering at all (Productions with
  missing dates are included normally).
- **A Production with no `premiere_date`:** excluded whenever `from_date` and/or
  `to_date` is supplied — its date range is entirely unknown, so it can't be said to
  overlap anything.
- **A Production with no `closing_date`** (but a known `premiere_date`): treated as
  an open-ended/ongoing run, so it always satisfies the `from_date` bound.
- **Only `from_date` supplied:** matches if `premiere_date` is known and the run
  hasn't already closed before `from_date` (`closing_date IS NULL OR closing_date >= from_date`).
- **Only `to_date` supplied:** matches if `premiere_date` is known and on or before
  `to_date`.
- **Both supplied:** both conditions above apply together (standard interval overlap).

#### Pagination and ordering

```json
{ "items": [], "total": 0, "limit": 20, "offset": 0 }
```

Results are always ordered `title ASC, id ASC` — the `id` tiebreaker keeps ordering
deterministic even when multiple Productions share the same title.

### Example requests

Minimal Production:

```bash
curl -X POST http://localhost:8000/api/v1/productions \
  -H "Content-Type: application/json" \
  -d '{"title": "Impro Night Berlin"}'
```

Production with full metadata (explicit slug):

```bash
curl -X POST http://localhost:8000/api/v1/productions \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Hamlet",
        "slug": "hamlet-schaubuehne-berlin",
        "work_title": "Hamlet",
        "creator_names": "William Shakespeare",
        "company_name": "Example Ensemble",
        "director_name": "Sample Director",
        "venue_name": "Example Theatre",
        "city": "Berlin",
        "country_code": "DE",
        "premiere_date": "2026-03-10",
        "closing_date": "2026-05-18"
      }'
```

Stand-up Production without Work or Venue metadata:

```bash
curl -X POST http://localhost:8000/api/v1/productions \
  -H "Content-Type: application/json" \
  -d '{"title": "Solo Stand-Up Hour", "creator_names": "Sample Comedian"}'
```

Update a Production:

```bash
curl -X PATCH http://localhost:8000/api/v1/productions/<id> \
  -H "Content-Type: application/json" \
  -d '{"city": "Munich"}'
```

Clear an optional field (explicit `null`):

```bash
curl -X PATCH http://localhost:8000/api/v1/productions/<id> \
  -H "Content-Type: application/json" \
  -d '{"venue_name": null}'
```

Filter Productions (German productions premiering in 2026 matching "hamlet"):

```bash
curl "http://localhost:8000/api/v1/productions?search=hamlet&country_code=DE&from_date=2026-01-01&to_date=2026-12-31"
```

Retrieve by slug:

```bash
curl http://localhost:8000/api/v1/productions/slug/hamlet-schaubuehne-berlin
```

### Frontend routes

- `/productions` — catalogue list (title, available metadata, links to detail pages).
  Shows a loading state (`app/productions/loading.tsx`), an inline error state if the
  API call fails, and an empty state if the catalogue has no Productions yet.
- `/productions/[slug]` — Production detail page. Renders a proper 404 (via Next.js
  `notFound()` / `not-found.tsx`) for an unknown slug. Optional fields with no value
  are simply omitted — there are no empty `Director:` / `Venue:` / `City:` labels.

Both pages fetch server-side via `INTERNAL_API_URL` (same pattern as the Phase 1 home
page), and there is no create/edit/delete UI — the catalogue is read-only in v0.1. A
basic filter UI was intentionally omitted (Phase 1 established no filter pattern to
follow); the backend filtering/search parameters above are fully implemented and can
be exercised directly against the API.

### Known limitations

- **`notFound()` and HTTP status codes:** because `/productions/loading.tsx` puts the
  `[slug]` page behind a streaming Suspense boundary, Next.js sends the `200` status
  before the `notFound()` result is known, so `/productions/<unknown-slug>` renders the
  correct "Production not found" page but reports HTTP `200` rather than `404` (Next.js
  still adds a `noindex` meta tag, so this does not affect search-engine indexing).
  This is a [documented Next.js App Router behavior](https://nextjs.org/docs/app/api-reference/file-conventions/loading#instant-loading-states),
  not specific to this codebase.
- **Slug auto-generation under true concurrent writes:** two simultaneous requests
  auto-generating a slug from the same title could both compute the same "next free"
  suffix before either commits; the database's unique constraint is the final
  safety net, so in that rare race one request would receive a `409` instead of
  silently retrying with a new suffix.
- **Backend hot-reload on macOS bind mounts** (pre-existing Phase 1 limitation, see
  above) also applies to the new Production code.

## Users & Authentication

Phase 4 adds minimal identity and authenticated ownership: registration, login,
logout, and a `/me` account summary. There are still no profiles, follows, OAuth,
password reset, email verification, or roles/permissions beyond "authenticated or
not" — those are explicitly out of scope until a later phase needs them.

### Session-cookie authentication (not JWT)

Authentication is a conventional **server-side session** backed by an **HTTP-only
cookie**, not a JWT:

```
Browser cookie (opaque, high-entropy token)
  → SHA-256 hash of the token
  → looked up against the `sessions` table (token_hash column)
  → Session row (if found, not expired)
  → associated User (eagerly loaded)
```

- The browser only ever holds an opaque random token in an `HttpOnly` cookie — it
  cannot be read by JavaScript, and there is nothing meaningful to steal via XSS.
- The database only ever stores a SHA-256 hash of that token (`sessions.token_hash`).
  A stolen database dump cannot be replayed as a valid session cookie, and the raw
  token is never logged.
- There is no `SESSION_SECRET_KEY`: tokens are opaque and looked up by their hash,
  never signed or decoded, so no server-side secret is needed to issue or verify one.

### Data model

- **`users`** — `id` (UUID), `username` (unique, indexed), `email` (unique, indexed,
  always stored lowercased + stripped), `password_hash` (Argon2id, never returned by
  any API response), `created_at`, `updated_at`. No profile fields.
- **`sessions`** — `id` (UUID), `user_id` (FK → `users.id`, `ON DELETE CASCADE`),
  `token_hash` (unique, indexed), `expires_at`, `created_at`. Sessions are immutable
  once created (looked up or deleted, never edited), so there is no `updated_at`.

Deleting a User cascades to their Sessions at the database level (`ON DELETE
CASCADE`), so there's no risk of orphaned session rows even for direct SQL deletes.

### Endpoints

| Method | Path                    | Behavior                                             |
|--------|-------------------------|-------------------------------------------------------|
| POST   | `/api/v1/auth/register` | Create a User + Session, set the cookie, return the User |
| POST   | `/api/v1/auth/login`    | Verify credentials, rotate the Session, set the cookie |
| POST   | `/api/v1/auth/logout`   | Delete the current Session (if any), clear the cookie  |
| GET    | `/api/v1/auth/me`       | Return the current User, or `401` if not authenticated |

All four accept/return JSON. `register` returns `201`, `login`/`me` return `200`,
`logout` returns `204`. `register`/`login` responses never include `password_hash`.

### Password & session security

- **Passwords** are hashed with **Argon2id** (via `pwdlib[argon2]`) — a memory-hard
  KDF designed for low-entropy, human-chosen secrets. Passwords must be 8-128
  characters; there are no arbitrary complexity rules (uppercase/symbol requirements
  etc.) beyond that minimum length.
- **Session tokens** are generated with `secrets.token_urlsafe(32)` (~256 bits of
  entropy) — the opposite case from passwords: already high-entropy, so a fast
  SHA-256 hash is appropriate (and intentionally *not* used for passwords).
- **Login failures** (wrong password *and* nonexistent email) return the identical
  generic `401 Invalid email or password` — the API never reveals whether an email
  is registered.
- **Session rotation:** logging in while an existing (valid, expired, or stale)
  session cookie is present deletes that session before issuing a new one, so
  repeated logins from the same browser don't accumulate redundant session rows.
  Registration always creates a fresh session (there is no pre-existing session to
  rotate at that point).
- **Expiry:** sessions default to a 30-day lifetime (`SESSION_LIFETIME_DAYS`). An
  expired session is treated as unauthenticated (`401`) and deleted opportunistically
  the next time it's looked up — there is no scheduled cleanup job in this phase.
- **CORS:** `allow_credentials=True` with an explicit, non-wildcard origin allowlist
  (`CORS_ORIGINS`) — required for the browser to send/receive the session cookie
  cross-origin (frontend on `:3000`, backend on `:8000`) in local development.

### Cookie configuration

| Setting     | Default      | Notes                                                        |
|-------------|--------------|---------------------------------------------------------------|
| Name        | `ts_session` | `SESSION_COOKIE_NAME`                                          |
| `HttpOnly`  | `true`       | always — never readable from JavaScript                       |
| `Secure`    | environment-dependent | `false` when `ENVIRONMENT=development` (plain HTTP locally), `true` otherwise |
| `SameSite`  | `Lax`        | always                                                         |
| `Path`      | `/`          | always                                                         |
| `Max-Age`   | 30 days      | `SESSION_LIFETIME_DAYS`                                        |

### Frontend routes

- **`/register`** — username, email, password. On success the user is already
  authenticated (registration creates a session), and the app navigates home.
- **`/login`** — email, password. Renders the backend's generic
  `Invalid email or password` error on failure; navigates home on success.
- **`/me`** — minimal authenticated account summary (username, email, member-since
  date). Prompts unauthenticated visitors to log in instead of exposing any data.
- **Navigation:** shows `Log in` / `Sign up` links when signed out, or a
  `USERNAME ▾` menu (Account, Log out) when signed in. Auth state is restored on
  every page load via `GET /api/v1/auth/me`, using a small React context
  (`components/auth-provider.tsx`) — no Redux/Zustand/NextAuth, and nothing is
  persisted independently in `localStorage`; the backend session is always the
  source of truth.
- Auth requests are added to the existing typed API-client pattern
  (`frontend/lib/auth.ts`, alongside `lib/api.ts` and `lib/productions.ts`) and use
  `credentials: "include"` so the browser sends/receives the session cookie;
  existing Production catalogue requests are unaffected.

### Example requests

Register:

```bash
curl -i -c cookies.txt -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "correct-horse-battery"}'
```

Log in (reusing the cookie jar from above, or a fresh one):

```bash
curl -i -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "correct-horse-battery"}'
```

Get the current user (sends the cookie saved above):

```bash
curl -i -b cookies.txt http://localhost:8000/api/v1/auth/me
```

Log out:

```bash
curl -i -b cookies.txt -X POST http://localhost:8000/api/v1/auth/logout
```

### Known limitations

- No password reset or email verification — a registered email is never confirmed.
- No multi-device session management UI: a User can hold multiple valid Sessions at
  once (one per browser/device that has logged in), and there is no way to list or
  revoke them individually. "Rotate on login" only replaces the session matching the
  cookie already present on that specific login request — it does not affect
  sessions on other devices.
- No scheduled cleanup of expired sessions; rows are removed opportunistically when
  encountered, which is acceptable at this scale but would need a periodic job later.

## Stopping, rebuilding, logs

```bash
# Stop containers (keeps the postgres_data volume, i.e. your data)
podman compose down

# Stop and view combined logs
podman compose logs -f

# Logs for a single service
podman compose logs -f backend

# Rebuild after changing a Dockerfile or dependency file
podman compose up --build

# Full reset, including deleting the Postgres volume (data loss!)
podman compose down -v
```

Source code is bind-mounted into the `frontend` and `backend` containers, so most code
edits take effect without rebuilding:

- **Frontend:** Next.js dev server hot-reloads automatically.
- **Backend:** `uvicorn --reload` watches for file changes. On some hosts (notably
  macOS with Podman's `virtiofs` file sharing), inotify events from bind mounts aren't
  always propagated reliably, so a change may not trigger an automatic reload. If that
  happens, restart the backend service: `podman compose restart backend`.

Dependencies (`node_modules`, the backend's `.venv`) are kept in named volumes
(`frontend_node_modules`, `backend_venv`) rather than the bind mount, so they survive
container restarts and aren't clobbered by the host directory. If you change
`package.json` or `pyproject.toml`, rebuild with `--build` so the volume gets the new
dependencies.

## Database migrations (Alembic)

Migrations run against whichever `DATABASE_URL` is active. The commands below run
migrations *inside* the running `backend` container (talking to the `postgres`
service); see [Local development](#local-non-container-development) to run them
against a host-installed Python/`uv` environment instead.

```bash
# Apply all pending migrations
podman compose exec backend uv run alembic upgrade head

# Autogenerate a new migration from model changes
podman compose exec backend uv run alembic revision --autogenerate -m "describe change"

# Roll back the most recent migration
podman compose exec backend uv run alembic downgrade -1

# Show current migration state
podman compose exec backend uv run alembic current
```

An initial, empty migration (`backend/alembic/versions/0001_initial.py`) establishes
the Alembic baseline. `0002_create_productions_table.py` creates the `productions`
table (see [Production Catalogue (v0.1)](#production-catalogue-v01)).
`0003_create_users_and_sessions_tables.py` creates the `users` and `sessions` tables
(see [Users & Authentication](#users--authentication)). All three are reversible
(`alembic downgrade -1` cleanly undoes the most recent one).

### Seed data

Once migrations are applied, seed the Production catalogue with sample data:

```bash
podman compose exec backend uv run python -m app.db.seed
# or: docker compose exec backend uv run python -m app.db.seed
```

The seed script is idempotent: it looks up each Production by its stable `slug`
before inserting, so running it again never creates duplicates.

## Local (non-container) development

You don't need this to run the app — it's only for running tests/linting without
containers, or for a faster backend edit loop than the bind-mount reload allows.

### Backend

Requires Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
cd backend
uv sync                       # installs deps from pyproject.toml + uv.lock into .venv
cp .env.example .env          # if not already done

# Run the dev server (requires Postgres reachable at DATABASE_URL, e.g. via
# `podman compose up postgres`)
uv run uvicorn app.main:app --reload

# Migrations against your local DATABASE_URL
uv run alembic upgrade head
```

`backend/pyproject.toml` is the single source of truth for backend dependencies;
`uv.lock` pins exact versions. There is no `requirements.txt` — it was not needed even
for the container build, since the `Dockerfile` runs `uv sync --frozen` directly
against `pyproject.toml` + `uv.lock`.

### Frontend

Requires Node.js 20+ and pnpm (the repo pins both via `volta` and the `packageManager`
field in `frontend/package.json`, so `corepack enable` / `volta install` will pick up
matching versions automatically).

```bash
cd frontend
pnpm install
cp .env.example .env.local    # if not already done
pnpm dev                      # requires the backend reachable at INTERNAL_API_URL
```

## Tests, linting, formatting, builds

Run these from inside each app's own environment (either `uv run` / `pnpm` on the host
per [Local development](#local-non-container-development) above, or via
`podman compose exec backend ...` / `podman compose exec frontend ...` against the
running containers).

### Backend (from `backend/`)

```bash
uv run ruff check .           # lint
uv run ruff format --check .  # format check (use `ruff format .` to fix)
uv run pytest                 # tests (health, app startup, Production catalogue, auth)
```

The Production catalogue and authentication tests exercise real SQL (case-insensitive
search, unique slugs/usernames/emails, ordering) against an actual PostgreSQL database
rather than a mocked session — consistent with the project's "async SQLAlchemy, no
mocking layer" approach. This means `pytest` requires a reachable database at
`DATABASE_URL` (e.g. `podman compose up -d postgres`, with `backend/.env` pointing at
`localhost:5432` as usual for host-side runs). The test suite creates the schema
automatically if missing and truncates the `productions`, `sessions`, and `users`
tables between tests for isolation, so it's safe to run repeatedly and does not
require running migrations first.

### Frontend (from `frontend/`)

```bash
pnpm lint            # ESLint
pnpm format:check     # Prettier check (use `pnpm format` to fix)
pnpm test             # Vitest + React Testing Library
pnpm build            # production build
```

## Continuous Integration

Every push and pull request targeting `main` runs `.github/workflows/ci.yml` on GitHub
Actions. It has two independent, parallel jobs — nothing here starts Postgres via
Compose or spins up the full container stack; each job only brings up what it needs.

### Frontend job

Runs from `frontend/`, using pnpm (via `pnpm/action-setup`, version read from the
`packageManager` field so it never drifts from local) and Node.js 20.20.2 (matching
the `volta` pin), with pnpm's store cached between runs:

```bash
pnpm install --frozen-lockfile
pnpm lint          # ESLint
pnpm typecheck      # tsc --noEmit
pnpm test           # Vitest + React Testing Library
pnpm build          # production build (NEXT_TELEMETRY_DISABLED=1, placeholder API URLs)
```

`pnpm typecheck` is a new script (`tsc --noEmit`, using the existing `strict: true`
`tsconfig.json`) added specifically to give CI a dedicated type-checking step; nothing
else about the frontend tooling changed. The build step sets `NEXT_PUBLIC_API_URL` and
`INTERNAL_API_URL` to harmless `localhost` placeholders — the app's dynamic routes
(`/`, `/productions`, `/productions/[slug]`) fetch data at request time, not at build
time, so no backend needs to be reachable for `pnpm build` to succeed.

### Backend job

Runs from `backend/`, using `uv` (via `astral-sh/setup-uv`, with its dependency cache
keyed on `backend/uv.lock`) and Python 3.12 (matching the `Dockerfile` and
`requires-python`). A `postgres:16` service container is started by GitHub Actions
itself (not Compose) with an explicit `pg_isready` health check; Actions blocks the
job's steps until it reports healthy, so no extra "wait for Postgres" step is needed.
The service is only reachable for the lifetime of the job and uses CI-only,
throw-away credentials — it has nothing to do with local development credentials:

```bash
uv sync --frozen
uv run ruff check .            # lint
uv run ruff format --check .   # format check
uv run alembic upgrade head    # verify migrations against a fresh DB
uv run pytest                  # tests
```

`DATABASE_URL` is set for the job to
`postgresql+asyncpg://postgres:postgres@localhost:5432/theatre_test` — `localhost`
because the service container's port is published back to the runner itself. Running
`alembic upgrade head` against this brand-new database (before `pytest`) proves the
migration chain builds the schema from empty; it's a genuine extra check, since the
test suite's own fixtures create the schema via `Base.metadata.create_all` and don't
strictly depend on the migrations having been run first. No backend type checker
(mypy/pyright) is configured in `pyproject.toml`, so none was added — the spec calls
for reusing existing tooling and only introducing something new where a check would
otherwise be impossible.

### Reproducing CI locally

The commands above are exactly what CI runs — no CI-only scripts or wrapper tooling
were introduced. To reproduce the backend job locally, point `DATABASE_URL` at a
disposable database (e.g. `podman compose up -d postgres`, then create a scratch
database) before running the `uv run` commands.

## Troubleshooting rootless Podman

- **`Error: creating lockfile ... operation not permitted`** or similar machine errors:
  make sure the Podman machine is initialized and running:
  `podman machine init` (once), then `podman machine start`.
- **Containers can't reach each other by service name:** confirm you're using
  `http://backend:8000` / `postgres` only *inside* container-to-container
  communication, never from the host or the browser. See
  [`backend:8000` vs `localhost:8000`](#backend8000-vs-localhost8000) above.
- **Port already in use on the host (`3000`, `8000`, or `5432`):** something else on
  your machine is bound to that port. Stop the other process, or change the published
  host port for the affected service in `compose.yml` (the container-internal port can
  stay the same).
- **Bind mount permission / SELinux errors** (mainly Fedora/RHEL hosts): the source
  bind mounts in `compose.yml` already use the `:Z` suffix, which tells Podman to
  relabel the mount for exclusive container access. This is safe and required on
  SELinux hosts; it's a no-op elsewhere (e.g. macOS, Docker). You should not need to
  `chmod` anything or disable SELinux.
- **No privileged/root containers required:** both the `frontend` and `backend` images
  run as a non-root `app` user; nothing in this setup needs `--privileged`, host
  networking, or Docker-socket access.
- **Backend code changes not picked up:** see the note on `virtiofs`/inotify under
  [Stopping, rebuilding, logs](#stopping-rebuilding-logs) — restart the backend
  service as a workaround.
- **Stale dependencies after changing `package.json` / `pyproject.toml`:** rebuild with
  `podman compose up --build` so the `frontend_node_modules` / `backend_venv` named
  volumes get repopulated from the new lockfile.
