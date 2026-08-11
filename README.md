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
(see [Users & Authentication](#users--authentication) below).

Phase 5 adds **Production Logging & Diary**: a signed-in user can log that they
attended a Production — an attendance record (`DiaryEntry`) with an optional
half-star rating and text review, viewable/editable at `/diary` (see [Production
Logging & Diary](#production-logging--diary) below). There is still no likes,
follows, comments, feeds, aggregate ratings, or public profiles.

Phase 6 adds **Azure Production Deployment & Continuous Delivery**: the frontend
and backend each run as their own Azure Container App, backed by Azure Database
for PostgreSQL Flexible Server, with GitHub Actions deploying to production
automatically on every merge to `main` once CI passes (see [Production
Deployment](#production-deployment) below). This phase is infrastructure and
deployment only — no new application functionality.

```
theatre-social/
├── frontend/           Next.js (TypeScript, App Router), pnpm
│   ├── Dockerfile        Dev image (bind-mounted source, `pnpm dev`)
│   └── Dockerfile.prod   Production image (standalone build, Azure Container Apps)
├── backend/            FastAPI, SQLAlchemy 2 (async), Alembic, uv
│   ├── Dockerfile        Dev image (bind-mounted source, `--reload`)
│   └── Dockerfile.prod   Production image (Azure Container Apps)
├── .github/workflows/  CI (every push/PR) + CD (main only, after CI passes)
├── compose.yml         Postgres + backend + frontend orchestration (local dev only)
├── .env.example        Compose-level environment variables
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

## Production Logging & Diary

Phase 5 adds the first core user activity: a signed-in user can log that they
attended a Production. A `DiaryEntry` is a record of one specific attendance — a
user may log the same Production multiple times (e.g. seeing the same run twice,
or a revival years later), and each attendance is its own row. There is
deliberately no unique constraint on `(user_id, production_id)`, and no upsert
behavior: logging a Production a second time always creates a new, independent
entry rather than overwriting the first.

```
Production = the thing that was seen
DiaryEntry = this user's record of seeing it (attendance + optional rating/review)
```

There are still no likes, comments, follows, activity feeds, public diary pages,
aggregate/average ratings, tags, lists, or viewing statistics — those are
explicitly out of scope until a later phase needs them.

### Data model

- **`diary_entries`** — `id` (UUID), `user_id` (FK → `users.id`, `ON DELETE
  CASCADE`), `production_id` (FK → `productions.id`, `ON DELETE RESTRICT`),
  `watched_at` (date, required, rejects future dates), `rating` (optional
  `SMALLINT`, 1-10 half-star units), `review` (optional `Text`, max 4000
  characters), `created_at`, `updated_at`.
- **Cascade behavior is intentionally asymmetric**: deleting a User deletes their
  diary history with it (same convention as `sessions.user_id`), but a Production
  with diary history **cannot** be deleted (`ON DELETE RESTRICT` — attempting to
  do so returns `409 Conflict`) so that a catalogue cleanup can never silently
  erase users' attendance history. Archiving/soft-deleting such a Production is
  left to a future phase.
- **Rating representation**: the public API and frontend always use a
  Letterboxd-style **0.5-5.0 scale in 0.5 increments**, but the database stores
  it as an integer **1-10 half-star count** (`rating = api_value * 2`) guarded by
  a `CHECK (rating IS NULL OR rating BETWEEN 1 AND 10)` constraint — this avoids
  storing an arbitrary float for what is really a 10-value discrete domain.
  Conversion is centralized in `backend/app/core/ratings.py` and never
  duplicated in routes or the frontend, which only ever sees 0.5-5.0.
- **Indexes**: a composite `(user_id, watched_at, created_at)` index backs the
  primary diary query (current user's entries, newest attendance first, with
  `created_at` then `id` as deterministic tiebreakers); `production_id` also has
  its own index, consistent with indexing foreign-key columns.

### Endpoints

| Method | Path                     | Behavior                                                       |
|--------|--------------------------|------------------------------------------------------------------|
| POST   | `/api/v1/diary`          | Create a diary entry for the current user (`404` if the Production doesn't exist) |
| GET    | `/api/v1/diary`          | List the current user's diary, paginated, `watched_at DESC, created_at DESC, id DESC` |
| GET    | `/api/v1/diary/{id}`     | Get one of the current user's diary entries                     |
| PATCH  | `/api/v1/diary/{id}`     | Partially update `watched_at`/`rating`/`review` (`production_id` is immutable) |
| DELETE | `/api/v1/diary/{id}`     | Delete one of the current user's diary entries                  |

All five require authentication (the same `get_current_user` session dependency
introduced in Phase 4) and derive `user_id` from the session — never from the
request body, a query parameter, or the URL. `GET /api/v1/diary` reuses the
existing generic `Page[T]` pagination envelope and embeds each entry's
`ProductionSummary` (the same schema the catalogue list already returns) so the
frontend never needs one extra request per entry.

An entry belonging to another user is indistinguishable from a nonexistent one:
both return `404`, not `403` — consistent with this project's existing
preference (see the auth system's single generic login error) for not revealing
information about resources a caller can't access.

### Frontend

- **Production detail page** — a prominent **"Log this production"** action.
  Unauthenticated visitors see a "Log in to log this production" prompt (reusing
  `useAuth`, the same session state Phase 4 established — no separate auth
  mechanism), rather than the button.
- **Log/review dialog** (`components/log-dialog.tsx`) — reused for both
  creating and editing an entry. Built on the native `<dialog>` element
  (`showModal()`), which provides focus trapping, Escape-to-close, and focus
  restoration without a UI library. Fields: date attended (defaults to today,
  browser `max` attribute plus authoritative backend validation), an optional
  half-star rating (`components/star-rating.tsx` — native radio inputs styled as
  stars, clearable via a separate "Clear rating" button since no rating value
  itself means "none"), and an optional review textarea. The only required
  field is the date; rating and review are enhancements to the log, not
  requirements.
- **`/diary`** — the signed-in user's chronological theatre history, newest
  attendance first, each entry showing date / production title (linked) /
  venue / rating (`★★★★½`-style) / review. Edit reopens the same dialog
  pre-filled; delete requires a confirmation click. Added to the nav for
  signed-in users.
- **Mutations without a reload**: both the production page and `/diary` update
  their own local React state from the mutation's response (`onSaved`/`onEdit`/
  `onDelete` callbacks) rather than using `router.refresh()` — consistent with
  the fact that both pages already render this data via client-side state
  (`useAuth`-gated Client Components, the same pattern `/me` established in
  Phase 4), not a Server Component fetch.
- **`frontend/lib/diary.ts`** extends the existing typed API-client pattern
  (`{ok, ...}` results, `credentials: "include"`) alongside `lib/auth.ts` and
  `lib/productions.ts`.

### Example requests

Log a production (reusing a cookie jar from a prior register/login):

```bash
curl -i -b cookies.txt -X POST http://localhost:8000/api/v1/diary \
  -H "Content-Type: application/json" \
  -d '{"production_id": "<production-uuid>", "watched_at": "2026-03-14", "rating": 4.5, "review": "A remarkable production."}'
```

List the current user's diary:

```bash
curl -s -b cookies.txt http://localhost:8000/api/v1/diary
```

Clear a rating/review on an existing entry:

```bash
curl -i -b cookies.txt -X PATCH http://localhost:8000/api/v1/diary/<entry-uuid> \
  -H "Content-Type: application/json" \
  -d '{"rating": null, "review": null}'
```

### Known limitations

- No aggregate/average ratings anywhere (Production catalogue or diary) — each
  `DiaryEntry` is only ever shown in the context of its own user.
- No pagination controls in the `/diary` UI yet — the API supports
  `limit`/`offset`, but the frontend always requests the first page.
- No spoiler handling, rich text, or review-length enforcement in the frontend
  beyond a `maxLength` attribute and a character counter — the backend's 4000
  character limit (`MAX_REVIEW_LENGTH` in `app/schemas/diary.py`) is
  authoritative.

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
(see [Users & Authentication](#users--authentication)). `0004_create_diary_entries_table.py`
creates the `diary_entries` table (see [Production Logging & Diary](#production-logging--diary)).
All four are reversible (`alembic downgrade -1` cleanly undoes the most recent one).

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
uv run pytest                 # tests (health, app startup, Production catalogue, auth, diary)
```

The Production catalogue, authentication, and diary tests exercise real SQL
(case-insensitive search, unique slugs/usernames/emails, ordering, foreign-key
`RESTRICT` behavior) against an actual PostgreSQL database rather than a mocked
session — consistent with the project's "async SQLAlchemy, no mocking layer"
approach. This means `pytest` requires a reachable database at `DATABASE_URL`
(e.g. `podman compose up -d postgres`, with `backend/.env` pointing at
`localhost:5432` as usual for host-side runs). The test suite creates the schema
automatically if missing and truncates the `productions`, `sessions`, `users`, and
`diary_entries` tables between tests for isolation, so it's safe to run repeatedly
and does not require running migrations first.

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

## Production Deployment

Phase 6 deploys the app to Azure: a frontend Azure Container App, a backend Azure
Container App, and Azure Database for PostgreSQL Flexible Server, wired together by a
GitHub Actions Continuous Delivery pipeline that runs after CI passes on `main`.
**Nothing here changes local development** — `podman compose up` (or `docker compose
up`) still works exactly as described above, and no Azure setting is required to run
the app locally.

```text
                    GitHub
                       │
                 GitHub Actions
              CI (every push/PR) ──► CD (main only, after CI)
                       │                        │
          ┌────────────┴──────────┐   migrate → deploy-backend → deploy-frontend
          │                       │             │                │
          ▼                       ▼             ▼                ▼
    Next.js frontend        FastAPI backend   Alembic          images pushed to
   Azure Container App     Azure Container App  upgrade         ghcr.io, then
                       │                │        head        `az containerapp update`
                       │   HTTPS API    │
                       └───────────────►│
                                        ▼
                          Azure Database for PostgreSQL
                                Flexible Server
```

### Architecture and why

| Component | Choice | Why |
| --- | --- | --- |
| Frontend hosting | Azure Container Apps | Next.js already builds a self-contained `output: "standalone"` server; a container gives full control over the Node process (start command, port, env vars) with no framework-specific adapter. Rejected **Static Web Apps**: its Next.js hybrid/SSR support has real adaptation and runtime constraints for App Router + a custom standalone server — not worth the risk. Rejected **App Service (Node.js runtime)**: viable, but its Oryx build/deploy pipeline would re-introduce framework-detection behavior the project doesn't need, for no benefit over a container we already know builds correctly. |
| Backend hosting | Azure Container Apps | FastAPI/Uvicorn is already containerized; Container Apps' consumption plan can **scale to zero**, unlike App Service's Basic/Standard plans (billed 24/7 regardless of traffic) — important for an MVP with ~no traffic. Using the same hosting model as the frontend also halves the number of deployment mechanisms to operate and document. |
| Container registry | GitHub Container Registry (`ghcr.io`) | Avoids an extra ~$5/mo Azure Container Registry resource; images stay registry-agnostic (portable to any other host later). |
| Database | Azure Database for PostgreSQL Flexible Server, Burstable `Standard_B1ms`, single zone | Cheapest general-purpose PostgreSQL tier suitable for an MVP; no HA/multi-zone, consistent with "cost visibility over premature scalability". |
| CI/CD | Existing `ci.yml`, extended with `migrate` / `deploy-backend` / `deploy-frontend` jobs | Reuses the existing quality gate instead of a second parallel workflow; `needs:` makes a failed lint/test/build block deployment without repeating that work. |
| Azure auth | OIDC via `azure/login`, no stored client secret | No long-lived credential to leak or rotate; federated credential is scoped to this repo's `production` GitHub Environment. |
| Migrations | `alembic upgrade head` as a CD step, before either app is deployed | Simplest reliable option — no Container Apps Jobs, no custom orchestration. |

### Azure resources required

| Resource | Purpose | SKU / tier |
| --- | --- | --- |
| Resource group `theatre-social-prod` | Groups every Phase 6 resource for easy cost tracking / cleanup | n/a |
| Container Apps Environment `theatre-social-env` | Shared hosting environment for both Container Apps (Log Analytics workspace included) | Consumption |
| Container App `theatre-social-backend` | Runs the FastAPI backend | Consumption, 0.25 vCPU / 0.5 GiB, 0–2 replicas |
| Container App `theatre-social-frontend` | Runs the Next.js frontend | Consumption, 0.25 vCPU / 0.5 GiB, 0–2 replicas |
| Azure Database for PostgreSQL Flexible Server (name of your choosing, globally unique) | Production database | Burstable `Standard_B1ms`, 32 GiB storage, PostgreSQL 16, single zone |
| GitHub Container Registry (`ghcr.io`, not an Azure resource) | Stores built backend/frontend images | Free (public packages) |
| Microsoft Entra App Registration `theatre-social-gha-deploy` | Federated identity GitHub Actions uses to authenticate to Azure | n/a (no cost) |

### Environment variables

| Name | Used by | Purpose | Secret? | Configured where |
| --- | --- | --- | --- | --- |
| `ENVIRONMENT` | backend | Switches cookie `Secure`/`SameSite` flags to production-strict | No | Backend Container App setting (`production`) |
| `DATABASE_URL` | backend, Alembic | asyncpg connection string to Azure Postgres | **Yes** | Backend Container App secret; `PROD_DATABASE_URL` GitHub Actions secret (used only by the `migrate` CD job) |
| `DATABASE_SSL_MODE` | backend, Alembic | TLS negotiation mode for the DB connection (`require` in prod) | No | Backend Container App setting; CD workflow env (`migrate` job) |
| `CORS_ORIGINS` | backend | Allowed browser origin(s) for the deployed frontend | No | Backend Container App setting |
| `SESSION_COOKIE_NAME` / `SESSION_LIFETIME_DAYS` | backend | Session cookie name/lifetime (optional, has defaults) | No | Backend Container App setting, only if overriding the default |
| `INTERNAL_API_URL` | frontend (server-side) | Backend URL used by Next.js server-side rendering/fetches | No | Frontend Container App setting |
| `NEXT_PUBLIC_API_URL` | frontend (browser-side) | Backend URL used by client-side `fetch` calls | No | **Docker build arg** (inlined at build time — see `frontend/Dockerfile.prod`), sourced from the `BACKEND_PUBLIC_URL` GitHub Actions repository variable |
| `PORT` | both (optional) | Overrides the port each app listens on (defaults: backend `8000`, frontend `3000`) | No | Container App setting, only if the target port ever needs to change |
| `AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID` | CD workflow (`azure/login`) | OIDC federated identity for GitHub Actions → Azure | **Yes** (repo secrets, not disclosed as secret *values*) | GitHub repository secrets |
| `AZURE_RESOURCE_GROUP` / `AZURE_BACKEND_APP_NAME` / `AZURE_FRONTEND_APP_NAME` / `BACKEND_PUBLIC_URL` | CD workflow | Names Azure resources to deploy to; backend's public URL for the frontend build | No | GitHub repository **variables** |

Never commit real values for any of the above — `.env.example` files only ever contain
placeholders (see `backend/.env.example` and `frontend/.env.example` for the exact
production block, commented out).

### Database SSL

Azure Database for PostgreSQL Flexible Server requires TLS. The obvious-looking fix —
adding `?sslmode=require` to `DATABASE_URL` — **does not work** with this stack:
SQLAlchemy's asyncpg dialect forwards every `DATABASE_URL` query parameter straight
through as a keyword argument to `asyncpg.connect()`, which has no `sslmode` parameter
(only `ssl`). Passing `sslmode=require` this way raises a `TypeError` at connection
time, not a working SSL connection.

Instead, `Settings.database_ssl_mode` (`app/core/config.py`) is a dedicated setting
passed as `connect_args={"ssl": ...}` to `create_async_engine` (`app/db/session.py`)
**and** to Alembic's own separately-constructed engine (`alembic/env.py`, which does
not reuse `app/db/session.py`). The value is forwarded to `asyncpg`, which understands
the libpq-style mode names directly (`disable` / `allow` / `prefer` / `require` /
`verify-ca` / `verify-full`).

- **Local/CI**: `DATABASE_SSL_MODE` is unset, defaulting to `"prefer"` — identical to
  the historical, unconfigured behavior against a non-SSL local/CI Postgres (verified:
  connects in plaintext, no behavior change).
- **Production**: `DATABASE_SSL_MODE=require` — verified against a local Postgres with
  no SSL listener that `require`/`True` correctly *fails* (proving it actually enforces
  TLS, not just requesting it opportunistically) while `prefer`/`disable`/`allow`
  succeed. `require` encrypts the connection but does not verify the server's
  certificate; `verify-full` is a stronger optional upgrade (see
  [Problems / compromises](#problems--compromises) in the deployment report for this
  phase, if you have it, or just set `DATABASE_SSL_MODE=verify-full` — the base Python
  image ships a CA bundle that should chain to Azure's public root CA).

Covered by `backend/tests/test_config.py` (the setting itself) and
`backend/tests/test_db_session.py` (that `create_engine()` actually wires it into
`connect_args`).

### Cross-site session cookie

Locally, the frontend (`localhost:3000`) and backend (`localhost:8000`) share the same
registrable domain ("localhost"), so `SameSite=Lax` works for the browser's
cross-origin `fetch(..., {credentials: "include"})` calls. In production the frontend
and backend are on **different** Azure hostnames — a genuinely cross-*site* setup —
and `Lax` cookies are withheld from cross-site `fetch`/XHR entirely (only sent on
top-level navigation), which would silently break `/me`, diary, etc. after a
seemingly-successful login. `Settings.session_cookie_samesite` (paired with the
existing `session_cookie_secure`, since browsers require `Secure` alongside
`SameSite=None`) fixes this: `Lax`/non-`Secure` in development, `None`/`Secure`
everywhere else — both derived from `ENVIRONMENT`, no separate flag needed.

### Continuous Delivery flow

`.github/workflows/ci.yml` now has five jobs. The original two are unchanged:

```text
Pull Request / any push
  ├── frontend   (lint, typecheck, test, build)
  └── backend    (lint, format check, migrate-from-empty, test)
```

Pushing to `main` runs those two jobs exactly as before, **plus** three more that only
run for `main` pushes (`if: github.ref == 'refs/heads/main' && github.event_name ==
'push'`) and only after both succeed (`needs: [frontend, backend]`):

```text
push to main
  ├── frontend ──┐
  └── backend  ──┤
                 ▼
              migrate            (alembic upgrade head, against Azure Postgres)
                 ▼
           deploy-backend        (build+push image, az containerapp update)
                 ▼
           deploy-frontend       (build+push image, az containerapp update)
```

- A failed `frontend`/`backend` job — or a failed `migrate`/`deploy-*` step — stops the
  chain there; nothing downstream runs, and the failure is visible directly in the
  GitHub Actions run.
- All three CD jobs share `concurrency: { group: cd-production, cancel-in-progress:
  false }`, so a second push to `main` while a deploy is in flight queues behind it
  instead of racing it.
- Nothing in the CD jobs repeats the frontend/backend lint/type-check/test/build work —
  they only build the already-tested code into a container image.
- Feature branches and pull requests never reach the CD jobs at all (the `if` guard on
  `migrate`).

### Azure OIDC authentication

GitHub Actions authenticates to Azure via `azure/login` using OpenID Connect — no
client secret is stored anywhere. The federated credential is scoped to this
repository's `production` GitHub Environment (`repo:<org>/<repo>:environment:production`),
and the identity's Azure role assignment is scoped to the `theatre-social-prod`
resource group only (`Contributor`) — not the subscription.

**Repository changes (already done by this phase):** the CD jobs in `ci.yml`
reference `${{ secrets.AZURE_CLIENT_ID }}`, `${{ secrets.AZURE_TENANT_ID }}`, `${{
secrets.AZURE_SUBSCRIPTION_ID }}`, `${{ secrets.PROD_DATABASE_URL }}`, and the
`${{ vars.* }}` repository variables listed in [Environment
variables](#environment-variables) above.

**GitHub manual configuration (you must do this):**
1. Create a GitHub Environment named `production` (**Settings → Environments → New
   environment**). Optionally add required reviewers/protection rules here later.
2. Add repository secrets (**Settings → Secrets and variables → Actions → Secrets**):
   `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `PROD_DATABASE_URL`.
3. Add repository variables (same page, **Variables** tab): `AZURE_RESOURCE_GROUP`,
   `AZURE_BACKEND_APP_NAME`, `AZURE_FRONTEND_APP_NAME`, `BACKEND_PUBLIC_URL`.

**Azure/Microsoft Entra manual configuration (you must do this):** see [Manual setup
guide](#manual-setup-guide) below for the exact commands — creating the App
Registration, its federated credential, and the RBAC role assignment.

### Manual setup guide

Everything below requires the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
logged in (`az login`) with an account that can create resources and role assignments,
plus Docker or Podman for the one-time bootstrap image builds. Replace
`<placeholders>` with real values; `<owner>/<repo>` is this GitHub repository's
`OWNER/REPO`. Pick any Azure region close to you — examples below use `westeurope`.

**1. Sign in and select the subscription**

```bash
az login
az account set --subscription "<SUBSCRIPTION_ID>"
```

**2. Create the resource group**

```bash
az group create --name theatre-social-prod --location westeurope
```

**3. Create the PostgreSQL Flexible Server**

Server names must be globally unique (they become
`<name>.postgres.database.azure.com`). Generate a strong admin password and store it
somewhere safe — you'll need it for `PROD_DATABASE_URL`.

```bash
az postgres flexible-server create \
  --name <UNIQUE-SERVER-NAME> \
  --resource-group theatre-social-prod \
  --location westeurope \
  --admin-user theatre_social_admin \
  --admin-password "<STRONG_PASSWORD>" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --version 16 \
  --high-availability Disabled \
  --public-access None

az postgres flexible-server db create \
  --resource-group theatre-social-prod \
  --server-name <UNIQUE-SERVER-NAME> \
  --database-name theatre_social
```

**4. Configure database networking (public access, MVP tradeoff)**

The CD pipeline's `migrate` job runs `alembic upgrade head` directly from a
GitHub-hosted runner, which has no fixed IP range Azure can allow-list precisely. For
this MVP, the firewall allows all public IPs — TLS (`require`) and Postgres
authentication are still fully enforced, but this is broader network exposure than
ideal; see [Problems / compromises](#problems--compromises) for the recommended
follow-up (self-hosted runner, VNet integration, or a Container Apps Job instead).

```bash
az postgres flexible-server firewall-rule create \
  --resource-group theatre-social-prod \
  --name <UNIQUE-SERVER-NAME> \
  --rule-name AllowAllForGitHubActions \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 255.255.255.255
```

Your `PROD_DATABASE_URL` (for the GitHub secret in step 9) is now:

```text
postgresql+asyncpg://theatre_social_admin:<STRONG_PASSWORD>@<UNIQUE-SERVER-NAME>.postgres.database.azure.com:5432/theatre_social
```

**5. Create the Container Apps Environment**

```bash
az extension add --name containerapp --upgrade
az containerapp env create \
  --name theatre-social-env \
  --resource-group theatre-social-prod \
  --location westeurope
```

**6. Bootstrap the backend Container App (one-time; CD takes over afterwards)**

```bash
cd backend
docker build -f Dockerfile.prod -t ghcr.io/<owner>/<repo>/backend:bootstrap .
docker login ghcr.io -u <your-github-username>   # use a PAT with write:packages
docker push ghcr.io/<owner>/<repo>/backend:bootstrap
cd ..
```

Make the `ghcr.io/<owner>/<repo>/backend` package **public** afterwards (GitHub →
your profile/org → Packages → the package → Package settings → Change visibility),
so Container Apps can pull it without extra registry credentials. If you'd rather keep
it private, add `--registry-server ghcr.io --registry-username <user>
--registry-password <PAT>` to the `az containerapp create` command below instead.

```bash
az containerapp create \
  --name theatre-social-backend \
  --resource-group theatre-social-prod \
  --environment theatre-social-env \
  --image ghcr.io/<owner>/<repo>/backend:bootstrap \
  --target-port 8000 \
  --ingress external \
  --min-replicas 0 --max-replicas 2 \
  --cpu 0.25 --memory 0.5Gi \
  --secrets database-url="<PROD_DATABASE_URL from step 4>" \
  --env-vars \
    ENVIRONMENT=production \
    DATABASE_SSL_MODE=require \
    DATABASE_URL=secretref:database-url \
    CORS_ORIGINS=https://placeholder.example

az containerapp show --name theatre-social-backend --resource-group theatre-social-prod \
  --query properties.configuration.ingress.fqdn -o tsv
# -> note this as BACKEND_PUBLIC_URL, prefixed with "https://"
```

**7. Bootstrap the frontend Container App**

```bash
cd frontend
docker build -f Dockerfile.prod -t ghcr.io/<owner>/<repo>/frontend:bootstrap \
  --build-arg NEXT_PUBLIC_API_URL="https://<backend-fqdn-from-step-6>" .
docker push ghcr.io/<owner>/<repo>/frontend:bootstrap
cd ..
```

Make this package public too (same steps as above), then:

```bash
az containerapp create \
  --name theatre-social-frontend \
  --resource-group theatre-social-prod \
  --environment theatre-social-env \
  --image ghcr.io/<owner>/<repo>/frontend:bootstrap \
  --target-port 3000 \
  --ingress external \
  --min-replicas 0 --max-replicas 2 \
  --cpu 0.25 --memory 0.5Gi \
  --env-vars \
    INTERNAL_API_URL="https://<backend-fqdn-from-step-6>" \
    NEXT_PUBLIC_API_URL="https://<backend-fqdn-from-step-6>"

az containerapp show --name theatre-social-frontend --resource-group theatre-social-prod \
  --query properties.configuration.ingress.fqdn -o tsv
```

**8. Point the backend's CORS at the real frontend URL**

```bash
az containerapp update --name theatre-social-backend --resource-group theatre-social-prod \
  --set-env-vars CORS_ORIGINS="https://<frontend-fqdn-from-step-7>"
```

**9. Configure the deployment identity (OIDC)**

```bash
APP_ID=$(az ad app create --display-name "theatre-social-gha-deploy" --query appId -o tsv)
az ad sp create --id "$APP_ID"

az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "theatre-social-github-production",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:<owner>/<repo>:environment:production",
  "audiences": ["api://AzureADTokenExchange"]
}'

RG_ID=$(az group show --name theatre-social-prod --query id -o tsv)
az role assignment create --assignee "$APP_ID" --role "Contributor" --scope "$RG_ID"

echo "AZURE_CLIENT_ID:       $APP_ID"
echo "AZURE_TENANT_ID:       $(az account show --query tenantId -o tsv)"
echo "AZURE_SUBSCRIPTION_ID: $(az account show --query id -o tsv)"
```

**10. GitHub repository configuration** — see [Azure OIDC
authentication](#azure-oidc-authentication) above for the exact secrets/variables to
add, using the values from steps 4, 6, 7, and 9.

**11. Run the initial migration and seed manually, once**

The very first deploy needs the schema and (optionally) seed data to exist before
anyone visits the site — do this once, by hand, before merging anything to `main`
(after that, `migrate` in CD keeps the schema current automatically):

```bash
cd backend
DATABASE_URL="<PROD_DATABASE_URL>" DATABASE_SSL_MODE=require uv run alembic upgrade head
DATABASE_URL="<PROD_DATABASE_URL>" DATABASE_SSL_MODE=require uv run python -m app.db.seed
```

**12. Trigger production deployment**

Merge a pull request into `main` (or push directly). Watch the `migrate` /
`deploy-backend` / `deploy-frontend` jobs in the **Actions** tab.

**13. Run the smoke tests**

See [Production smoke testing](#production-smoke-testing) below.

### Database migrations

- **When**: automatically, in the `migrate` CD job, before either app is redeployed —
  on every push to `main` that passes CI.
- **Where**: on the GitHub-hosted runner, connecting directly to the Azure Postgres
  public endpoint (no Azure API access needed for this step, so it doesn't use
  `azure/login`).
- **Which credentials**: the `PROD_DATABASE_URL` GitHub secret (the same admin login
  created in Manual setup guide step 3).
- **On failure**: the job fails, `deploy-backend`/`deploy-frontend` never run (via
  `needs:`), and neither Container App is touched — production keeps running its
  previous (already-migrated) version.
- **Manual run**: `cd backend && DATABASE_URL="<PROD_DATABASE_URL>" DATABASE_SSL_MODE=require uv run alembic upgrade head`
  from any machine with network access to the database (e.g. your own machine, once
  the firewall rule from step 4 is in place).
- Only ever runs `alembic upgrade head` — forward migrations only. No automatic
  downgrades, ever (see [Rollback](#rollback-and-failure-handling)).

### Production seed data

The seed script (`backend/app/db/seed.py`) is unchanged from local development and
already idempotent — it looks up each Production by its stable `slug` before
inserting, so re-running it is always safe and never deletes or overwrites existing
data (including any real user-created data, since it only ever touches the
`productions` table by `slug`).

**Alembic migrations** (schema) and **seed data** (a fixed set of example
Productions) are separate concerns: migrations run automatically in CD; seeding is a
deliberate, manual, one-time action for a fresh environment — the CD pipeline never
runs the seed script.

```bash
cd backend
DATABASE_URL="<PROD_DATABASE_URL>" DATABASE_SSL_MODE=require uv run python -m app.db.seed
```

### Health checks

`GET /health` (`backend/app/api/routes/health.py`) runs a real `SELECT 1` against the
database and returns `200 {"status": "ok", "database": "connected"}` or `503
{"status": "error", "database": "disconnected", "detail": "Database connection
failed"}` — it verifies both "the process is running" and "the database is reachable",
without ever exposing credentials, stack traces, or infrastructure details. This was
already true before Phase 6; no changes were needed.

Azure Container Apps' liveness/readiness probes are not configured with a custom path
by default; if you want them pointed at `/health` explicitly:

```bash
az containerapp update --name theatre-social-backend --resource-group theatre-social-prod \
  --set-probe-path liveness=/health
```

Frontend has no equivalent endpoint — the root page itself (a normal HTTP `200`) is
sufficient as a liveness signal for the Container App.

### Logs and observability

- **Backend/frontend logs**: `az containerapp logs show --name <app-name>
  --resource-group theatre-social-prod --follow` (Container Apps ships stdout/stderr
  to the environment's Log Analytics workspace automatically — no extra setup).
- **Deployment failures**: visible directly in the GitHub Actions run (Actions tab →
  the failed job/step).
- **Startup failures**: `az containerapp revision list` / `az containerapp logs show`
  surface container crashes and their exit reasons.
- **Optional improvement**: Azure Application Insights can be added later with very
  little code (`--enable-dapr`-style app setting + the Python/Node SDK) — deliberately
  not added in this phase to keep observability minimal, per scope.
- Explicitly not introduced: Prometheus, Grafana, OpenTelemetry infrastructure, ELK,
  distributed tracing.

### Deployment procedure

Normal flow: open a PR → CI runs → merge to `main` → CD runs automatically (`migrate`
→ `deploy-backend` → `deploy-frontend`). Nothing to trigger by hand.

### Rollback and failure handling

- **Redeploy a previous backend/frontend version**: every image is tagged with its
  commit SHA (`ghcr.io/<owner>/<repo>/backend:<sha>`, similarly for `frontend`), so
  rolling back is:
  ```bash
  az containerapp update --name theatre-social-backend --resource-group theatre-social-prod \
    --image ghcr.io/<owner>/<repo>/backend:<previous-good-sha>
  ```
  (substitute `theatre-social-frontend`/`frontend` for the frontend). Container Apps
  also keeps prior revisions; `az containerapp revision list` / `az containerapp
  ingress traffic set` can shift traffic back to an older revision without a rebuild.
- **GitHub Actions failures**: a failed job stops the pipeline at that point (see
  [Continuous Delivery flow](#continuous-delivery-flow)); re-running after a fix
  re-triggers from a fresh push (or **Actions → Re-run jobs**).
- **Alembic migration failure**: the `migrate` job fails, deployment never proceeds,
  and the database is left at whatever the failed migration did/didn't complete —
  **there is no automatic downgrade**. Fix forward (a new migration) or manually
  investigate/repair the schema; `alembic downgrade` is a manual, deliberate action
  only, never automatic.
- Application rollback (redeploy an old image) and database rollback (schema/data) are
  **different operations** — rolling back the app never implies rolling back the
  database, and vice versa.

### Production smoke testing

After any deployment, verify manually (or via `curl`/browser):

1. Frontend loads publicly at its Container App URL.
2. `GET /health` on the backend URL returns `200`.
3. (implied by #2) backend successfully reached Azure PostgreSQL.
4. `alembic current` (run locally against `PROD_DATABASE_URL`) matches the latest
   revision in `backend/alembic/versions/`.
5. `/productions` loads the catalogue.
6. Register a new account.
7. Log in with it.
8. Refresh the page — still logged in (`/me` persists).
9. Open a production detail page.
10. "Log this production" creates a diary entry.
11. Set a rating — persists.
12. Set/change the watched date — persists.
13. Add review text — persists.
14. `/diary` shows the new entry.
15. Log out, log back in — the diary entry is still there.
16. From a second browser/incognito session (no cookie), attempting to modify the
    first user's diary entry via the API is rejected (401/404, matching existing
    ownership rules).
17. Redeploy (push a trivial change to `main`) — the app is still fully functional
    afterwards.

*(This list intentionally excludes "rewatch flag", "tags", and "private flag" from the
original Phase 6 prompt's checklist template — those fields don't exist on
`DiaryEntry`; see [Production Logging & Diary](#production-logging--diary) above for
the actual fields Phase 5 implemented: `watched_at`, `rating`, `review`.)*

**I have not deployed this to a real Azure subscription** (no Azure account/credentials
are available in this environment), so every item above is reported as **NOT TESTED**
in this phase's final report rather than claimed as passing — see that report for the
full, honest breakdown, and re-run this checklist yourself after following the [Manual
setup guide](#manual-setup-guide).

### Costs

Approximate West Europe, pay-as-you-go pricing (check the
[Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/) for
current numbers — these change over time and by region):

| Resource | Idle cost | Notes |
| --- | --- | --- |
| Container Apps Environment + 2 apps (Consumption, 0.25 vCPU/0.5 GiB each, `min-replicas 0`) | ~$0/month idle | Scales to zero with no traffic; charged per vCPU-second/GiB-second only while running. Light MVP traffic: a few dollars/month. |
| PostgreSQL Flexible Server, Burstable `Standard_B1ms`, 32 GiB | ~$12–15/month | **Does not scale to zero** — Flexible Server is always-on while it exists; this is the dominant fixed cost. Stop it (`az postgres flexible-server stop`, auto-restarts after 7 days) to pause billing for compute (storage is still billed while stopped). |
| Log Analytics workspace (created with the Container Apps Environment) | ~$0–2/month | Pay-per-GB ingested; MVP log volume is tiny. |
| GitHub Container Registry | $0 | Free for public packages. |
| Microsoft Entra App Registration | $0 | No cost. |

**Total**: roughly **$12–20/month** for an idle-to-light-traffic MVP, dominated by the
always-on database.

**Stopping/deleting:**
```bash
# Pause the database (compute only; storage still billed) without deleting data:
az postgres flexible-server stop --name <server-name> --resource-group theatre-social-prod

# Delete everything for this phase in one shot:
az group delete --name theatre-social-prod --yes --no-wait
```

### Local development after Phase 6

Unchanged. `podman compose up --build` (or `docker compose up --build`) still starts
Postgres + backend + frontend exactly as described in [Start the
stack](#2-start-the-stack) above. No Azure account, credentials, or setting is
required for local startup — `DATABASE_SSL_MODE` and the cross-site cookie setting
both default to their local-friendly values when `ENVIRONMENT`/`DATABASE_SSL_MODE`
are simply left unset.

### Portability

Nothing added in this phase creates meaningful Azure lock-in:

- The app still depends only on standard technologies: Next.js, Node.js, FastAPI,
  PostgreSQL, `asyncpg`, SQLAlchemy, Alembic, plain environment variables, OCI
  containers, and GitHub Actions.
- No Azure SDK is used in application code — the backend/frontend don't know they're
  running on Azure at all; every Azure-specific detail lives in the Dockerfiles' `CMD`
  (reads `$PORT` like any other container platform would expect) and the CD workflow.
- Images are stored in GitHub Container Registry, not an Azure-specific registry.
- Migrating the database to, say, Amazon RDS for PostgreSQL is a `DATABASE_URL`
  change plus (if not using RDS's own TLS setup) an equivalent `DATABASE_SSL_MODE`
  value — no code change.
- Migrating hosting to another container platform (Fly.io, Render, AWS, etc.) is a
  matter of pointing that platform at the same `Dockerfile.prod` images and setting
  the same environment variables — the CD workflow's `az containerapp update` calls
  are the only Azure-specific lines in the entire pipeline.
