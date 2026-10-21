# Development roadmap

Phased history and **proposed** future work for Theatre Social. Completed
milestones are grounded in git history and merged pull requests. Future phases
are proposals — not commitments — and have no invented deadlines or progress
percentages.

Related: [architecture.md](architecture.md), [AGENTS.md](../AGENTS.md),
[README.md](../README.md).

## Completed milestones

### Phase 1 — Foundation

**PR:** [#1](https://github.com/cariocaphil/theatre-social/pull/1)  
**Branch:** `feature/1-project-foundation`

Monorepo scaffolding: Next.js frontend, FastAPI backend, PostgreSQL via Compose,
`/health` with real DB connectivity check, Alembic baseline, local env examples,
and initial test/lint tooling.

### Phase 2 — Production Catalogue (v0.1)

**PR:** [#2](https://github.com/cariocaphil/theatre-social/pull/2)  
**Branch:** `feature/2-production-catalogue`

First domain feature: `Production` model and CRUD/list API with search/filters,
slug uniqueness, pagination, seed data, and frontend catalogue list/detail
pages. Work/venue remain optional text fields on Production (not separate
entities).

### Phase 3 — Continuous Integration

**PR:** [#3](https://github.com/cariocaphil/theatre-social/pull/3)  
**Branch:** `feature/3-continuous-integration`

GitHub Actions quality gate on pushes/PRs to `main`: frontend
lint/typecheck/test/build and backend lint/format/migrate/test against a
Postgres service container. CI only — no deployment in this phase.

### Phase 4 — Users & Authentication

**PR:** [#4](https://github.com/cariocaphil/theatre-social/pull/4)  
**Branch:** `feature/4-users-authentication`

Minimal accounts: register/login/logout/`/me`, Argon2id passwords, server-side
sessions with HTTP-only cookie, frontend auth UI and `AuthProvider`. No
profiles, OAuth, or password reset.

### Phase 5 — Production Logging & Diary

**PR:** [#5](https://github.com/cariocaphil/theatre-social/pull/5)  
**Branch:** `feature/5-logging-and-diary`

Signed-in users log attendances as `DiaryEntry` records (date, optional
half-star rating, optional review), including multiple logs of the same
Production. Diary API + `/diary` UI and “Log this production” on detail pages.
No social graph, public reviews, or aggregate ratings.

### Phase 6 — Azure Deployment & Continuous Delivery

**PR:** [#6](https://github.com/cariocaphil/theatre-social/pull/6)  
**Branch:** `feature/6-azure-cd`

Production hosting preparation: production Dockerfiles, DB SSL settings,
cross-site session cookie behavior, README manual Azure setup, and CD jobs in
`ci.yml` (migrate → deploy backend → deploy frontend) using OIDC to Azure and
images on ghcr.io.

**Follow-ups visible in git after merge (not separate roadmap phases):**
temporary frontend bootstrap workflow experiments (later removed), and
`fix: use environment variables for Azure OIDC` (OIDC client/tenant/subscription
IDs read from GitHub **variables**, while `PROD_DATABASE_URL` remains a secret).

Whether a given Azure subscription is currently live is an operational fact
outside the repository — the *code and workflow* for deployment are what this
phase delivered.

---

## Current phase

### Phase 7 — Engineering Documentation & Agent Instructions

**Branch:** `docs/7-engineering-foundation`  
**Status:** in progress (documentation only)

**Scope:**

- Root [AGENTS.md](../AGENTS.md)
- [docs/architecture.md](architecture.md)
- This roadmap (`docs/roadmap.md`)
- Lightweight ADR conventions in [docs/decisions/](decisions/README.md)
- README navigation into the documentation set

**Non-goals:** application behavior, dependencies, schemas, CI/CD workflow
logic, or new agent frameworks.

**Completion criteria:**

- Agents and humans can find architecture, conventions, and next-work proposals
  without reverse-engineering the monorepo.
- Implemented vs proposed work is clearly separated.
- Documentation matches the repository (commands, versions, CD variable layout).

---

## Proposed future phases

These are **proposed** groupings. Several topics may be combined or reordered
once MVP priorities are clearer. Dependencies are relative to the completed
phases above.

### Proposed Phase 8 — Production hardening & operational reliability

**Objective:** Make the Azure deployment safer and easier to operate without
changing product features.

**Done:**

- Automated post-deployment smoke (`ci/9-post-deployment-smoke-tests` / PR 9) —
  CD job `smoke-test` runs read-only public checks (`/health`,
  `/api/v1/productions`, frontend `/`) after both Container Apps update; mock
  tests for `scripts/smoke-prod.sh` run on every CI push/PR.
- Production deployment serialization (`ci/10-serialize-production-deployments`
  / PR 10) — workflow-level concurrency on `main` keeps one full sequence
  (migrate → deploy-backend → deploy-frontend → smoke-test, including preceding
  CI) from being cancelled mid-flight; job-level `cd-production` including smoke
  is limited defense in depth. Pending main runs can still be replaced (not every
  commit necessarily deploys).

**Related (product):** review-text publication on diary entries
(`feature/11-production-reviews` / PR 11) — `published_at`, publish/unpublish
APIs, public `GET …/productions/{id}/reviews`, LogDialog visibility controls.
Production-page public reviews UI and profiles remain separate follow-ups
(see Phase 11). Mark this Done in Completed milestones once the PR merges.

**Still proposed:**

- Tighten Postgres network exposure (replace “allow all” firewall if still in
  use; prefer runner/job with constrained access for migrations).
- Optional `DATABASE_SSL_MODE=verify-full` validation against Azure.
- Confirm the manual auth/diary smoke checklist against a live subscription.
- Minimal structured logging / optional Application Insights (docs-first if
  code changes stay tiny).

**Dependencies:** Phase 6 deployment machinery.  
**Completion criteria:** Documented production access path with fewer MVP
security compromises; automated smoke green on real deploys; remaining hardening
items above addressed or explicitly deferred.  
**Priority:** High (stabilizes everything else that ships to production).

### Proposed Phase 9 — Catalogue curation & data quality

**Objective:** Improve how Productions enter and stay trustworthy in the
catalogue.

**Candidate scope:**

- Authenticated (or admin) create/edit flows beyond raw API/seed.
- Dedup/slug collision UX; clearer handling of incomplete metadata.
- Optional ingestion from curated sources (manual import first; automated
  scrapers only with strong provenance rules).
- Soft-delete / archive for Productions that have diary history (instead of
  hard delete + `409`).

**Dependencies:** Phases 2, 4, 5 (ownership of diary history).  
**Completion criteria:** Operators/users can maintain catalogue entries without
SQL/seed; deletion/archive policy documented and implemented.  
**Priority:** High for product usefulness; domain questions below should inform
schema changes.

### Proposed Phase 10 — Theatre domain modeling (works, venues, runs)

**Objective:** Evolve beyond flat text metadata where the product needs it.

**Candidate scope (only after answering open questions):**

- Optional `Work` and/or `Venue` entities linked from Production.
- Clearer representation of runs, revivals, and touring (may remain metadata
  longer if identity rules are unclear).
- Migration plan that preserves existing diary/production IDs.

**Dependencies:** Phase 9 curation patterns; answers to open architectural
questions.  
**Completion criteria:** Explicit model for at least one extracted concept
(Work or Venue) with migrations and API/UI updates; no silent data loss.  
**Priority:** Medium — valuable, but premature extraction is costly.

### Proposed Phase 11 — Profiles & lightweight social layer

**Objective:** First social surface beyond a private diary.

**Candidate scope:**

- Public profile basics (display name, optional bio) — still minimal.
- Optional public diary visibility / follow relationships (start tiny).
- Explicitly defer feeds, likes, comments, DMs unless a thin MVP proves needed.

**Dependencies:** Phases 4–5.  
**Completion criteria:** Users can discover each other through a defined,
privacy-respecting surface; diary privacy defaults remain safe.  
**Priority:** Medium — after catalogue quality is credible.

### Proposed Phase 12 — Discovery, search, and recommendations

**Objective:** Help users find productions and diary-worthy shows.

**Candidate scope:**

- Richer catalogue search/filter UX (API already has several filters).
- Saved searches or lists (if still simple).
- Recommendations only if grounded in diary signals and explainable — avoid
  opaque ML platform work early.

**Dependencies:** Solid catalogue (9) and enough diary usage (5).  
**Completion criteria:** Measurable improvement in finding productions; no
dependency on heavyweight recommendation infrastructure unless justified.  
**Priority:** Medium/Low until catalogue volume justifies it.

### Proposed Phase 13 — Accessibility & frontend experience

**Objective:** Raise baseline UX quality without redesigning the product.

**Candidate scope:**

- Accessibility pass (keyboard, labels, contrast, dialog patterns already
  partly in place).
- Responsive polish; loading/error empty states consistency.
- Performance hygiene for catalogue/diary lists.

**Dependencies:** None hard — can proceed incrementally anytime.  
**Completion criteria:** Documented a11y checklist exercised on main flows;
no regressions in existing Vitest coverage.  
**Priority:** Ongoing / Medium — schedule alongside feature work rather than
only as a late big-bang.

---

## Open architectural questions

These are deliberately **unresolved**. Do not invent schema or product rules
to “finish” them in documentation alone.

1. **What uniquely identifies a theatre production?**  
   Title + venue + dates? Company + work + premiere? External IDs? How do we
   treat incomplete rows?

2. **How should performances, revivals, and touring productions be represented?**  
   One Production per run? Per tour stop? Parent/child runs? Diary entries
   already allow multiple attendances of the same Production — that interacts
   with whatever run model we choose.

3. **When should works and venues become independent entities?**  
   The codebase intentionally keeps them as text today. Extraction should wait
   until curation/search/dedup pain is concrete.

4. **How should external production information be sourced and verified?**  
   Manual entry, partner feeds, scraping, user submissions? What is the
   provenance and trust model?

5. **How should user-contributed data be moderated?**  
   Especially once catalogue writes or public social surfaces exist.

6. **How should the platform handle incomplete or conflicting metadata?**  
   Display rules, merge/dedup tooling, and whether “unknown” is first-class.

Record durable answers as ADRs under [docs/decisions/](decisions/README.md)
when a decision is actually made in implementation.
