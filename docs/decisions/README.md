# Architectural Decision Records (ADRs)

Lightweight convention for recording significant decisions in this repository.

Do **not** create ADRs for every change. Prefer updating
[architecture.md](../architecture.md) or the relevant README section when a
decision is small or already obvious from the code.

## When an ADR is useful

Write an ADR when the decision involves one or more of:

- Significant **domain modeling** choices (e.g. extracting Work/Venue, how runs
  and revivals relate to Production and DiaryEntry).
- **Authentication or security** architecture (session model, cookie policy,
  TLS requirements, network exposure).
- **Database or deployment** strategy (hosting, migration approach, SSL,
  registry choice).
- Major **technology additions or replacements** (new packages, new services,
  abandoning an existing stack piece).

Skip ADRs for routine features that follow existing patterns (another CRUD
endpoint in the same layered style, another Vitest file, docstring polish).

## Do not invent history

Do not generate retrospective ADRs for Phases 1–6 unless contemporaneous
evidence (PR discussion, README rationale, commit messages) is enough to state
context and alternatives accurately. Prefer documenting *new* decisions going
forward.

## File naming

```text
docs/decisions/NNNN-short-title.md
```

Use a zero-padded sequential number (`0001`, `0002`, …) and a short kebab-case
title. Example: `0001-session-cookie-auth.md`.

## Template

Copy the block below into a new file:

```markdown
# NNNN. Title

- **Status:** Proposed | Accepted | Superseded | Deprecated
- **Date:** YYYY-MM-DD
- **Deciders:** (optional)

## Context

What problem or force requires a decision? Link related issues/PRs/docs.

## Decision

What we chose to do.

## Alternatives considered

- Alternative A — why not
- Alternative B — why not

## Consequences

Positive, negative, and follow-up implications. Note anything that should
update `docs/architecture.md` or the README.
```

## Status meanings

| Status | Meaning |
| --- | --- |
| Proposed | Under discussion; not yet binding |
| Accepted | Current decision; implement accordingly |
| Superseded | Replaced by a newer ADR (link it) |
| Deprecated | No longer applicable; kept for history |

Keep ADRs short. Bureaucracy is not a goal — durable clarity is.
