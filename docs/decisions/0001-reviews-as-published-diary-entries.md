# 0001. Reviews as published diary entries

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Theatre Social maintainers

## Context

Phase 5 already stores optional review text on `DiaryEntry`. PR 11 needs
explicit publication of that text without duplicating diary/logging.

## Decision

Extend `DiaryEntry` with nullable `published_at`. Published review text is
rows where `published_at IS NOT NULL` and `review` is non-empty. Do not
introduce a separate `Review` table. Keep `watched_at` required (no
attendance-less reviews in this PR).

Attendance logging and review-text visibility are independent: only review
text becomes public when published; this PR does not ship public attendance
feeds.

## Alternatives considered

- Separate `Review` entity — clearer social model, but duplicates or syncs
  rating/review with diary and adds API/UI surface for little MVP gain.
- Nullable `watched_at` for review-only rows — deferred; not required for
  publication of existing log-time reviews.

## Consequences

- Public list: `GET /api/v1/productions/{id}/reviews`.
- Owner publish/unpublish via diary routes and atomic `publish_review` on
  create/update.
- UI for browsing public reviews on production pages is a follow-up PR.
- Update `docs/architecture.md` and the roadmap when this ships.
