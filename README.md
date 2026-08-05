# Theatre Social

Monorepo foundation for Theatre Social: a Next.js (TypeScript, App Router) frontend, a
FastAPI (Python, async SQLAlchemy 2 + `asyncpg`) backend, and PostgreSQL, orchestrated
with an OCI-compatible Compose file that works with rootless Podman or Docker.

This repository currently contains only the **foundation**: project scaffolding, a
`/health` endpoint that verifies database connectivity end-to-end, and the container /
migration / testing setup needed to build real features on top of it. There is no
authentication, user data, or domain logic yet.

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
- **Backend health check:** http://localhost:8000/health
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

An initial, empty migration (`backend/alembic/versions/0001_initial.py`) is included so
the migration chain has a known starting point. There are no domain tables yet.

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
uv run pytest                 # tests (health success / db-unavailable / app startup)
```

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
