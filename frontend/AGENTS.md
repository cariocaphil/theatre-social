# Frontend agent notes

Extends root [AGENTS.md](../AGENTS.md). Open when working under `frontend/`.

## Data fetching

- Server Components / Node: `INTERNAL_API_URL`
- Browser: `NEXT_PUBLIC_API_URL` + `credentials: "include"`
- API helpers: `{ ok: true, data }` / `{ ok: false, error }` — do not throw for
  expected failures

## Layout

`app/` (App Router) · `components/` · `lib/` (typed API clients)

## Verify (from `frontend/`)

Same checks as the CI frontend job, plus format check:

```bash
pnpm lint
pnpm typecheck
pnpm format:check
pnpm test
pnpm build
```

`pnpm build` needs `NEXT_PUBLIC_API_URL` / `INTERNAL_API_URL` (inlined at build
time; CI uses placeholders). Recipes: README.
