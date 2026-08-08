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
- **Backend health check:** http://localhost:8000/health
- **Production catalogue API:** http://localhost:8000/api/v1/productions
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
the Alembic baseline. `backend/alembic/versions/0002_create_productions_table.py`
creates the `productions` table (see [Production Catalogue (v0.1)](#production-catalogue-v01)).
Both are reversible (`alembic downgrade -1` cleanly undoes either one).

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
uv run pytest                 # tests (health, app startup, Production catalogue)
```

The Production catalogue tests exercise real SQL (case-insensitive search, unique
slugs, ordering) against an actual PostgreSQL database rather than a mocked session —
consistent with the project's "async SQLAlchemy, no mocking layer" approach. This
means `pytest` requires a reachable database at `DATABASE_URL` (e.g.
`podman compose up -d postgres`, with `backend/.env` pointing at `localhost:5432` as
usual for host-side runs). The test suite creates the schema automatically if missing
and truncates the `productions` table between tests for isolation, so it's safe to run
repeatedly and does not require running migrations first.

### Frontend (from `frontend/`)

```bash
pnpm lint            # ESLint
pnpm format:check     # Prettier check (use `pnpm format` to fix)
pnpm test             # Vitest + React Testing Library
pnpm build            # production build
```

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
