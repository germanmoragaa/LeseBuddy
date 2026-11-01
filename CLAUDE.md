# CLAUDE.md

## What this is

LeseBuddy is a portfolio web app for German learners. Users paste a German text, see a
difficulty estimate, select words/expressions to get contextual explanations, save them to a
vocabulary library, and review them as spaced-repetition flashcards.

The full product and engineering plan lives in [docs/blueprint.md](docs/blueprint.md) — read it
before starting new work, especially the stack (section 4), repo structure (section 5), backlog
(section 12), and build order (section 16). Treat the repo structure there as a starting point:
add folders only when the current step needs them.

## Stack

- **Frontend:** React + TypeScript + Vite, Tailwind CSS v4, TanStack Query, react-router,
  lucide-react, self-hosted DM Sans (`@fontsource/dm-sans`)
- **Backend:** Python + FastAPI, Pydantic
- **Database:** PostgreSQL 18 (Docker Compose) with SQLAlchemy 2.0 (sync, `psycopg` v3 driver) and
  Alembic migrations
- **NLP:** spaCy German model (not set up yet)
- **AI:** LLM behind a provider interface (not set up yet)
- **Testing:** pytest (backend), Vitest + React Testing Library (frontend), Playwright (e2e, not
  set up yet)

## Running things

### Database

```bash
docker compose up -d   # starts Postgres 18; creates both lesebuddy and lesebuddy_test
```

### Backend (`backend/`)

```bash
cd backend
cp .env.example .env              # first time only; defaults already match docker-compose.yml
uv run alembic upgrade head        # apply migrations to the dev DB
uv run fastapi dev app/main.py     # dev server, http://localhost:8000
uv run pytest                      # tests (migrate + isolate lesebuddy_test automatically)
uv run ruff check .                # lint

# new/changed models:
uv run alembic revision --autogenerate -m "describe the change"   # then review the file by hand
```

`Settings` (`app/core/config.py`) has localhost defaults matching `docker-compose.yml`, so the
app and `alembic` work without `.env` present as long as Postgres is reachable at
`localhost:5432`; `.env` only needs to exist to override those defaults.

### Frontend (`frontend/`)

```bash
cd frontend
npm run dev         # dev server, http://localhost:5173, proxies /api -> localhost:8000
npm run build
npm test            # vitest run
npm run lint         # oxlint
npm run typecheck    # tsc -b
```

Run the backend before the frontend if you need `/api/v1/...` calls to resolve — the Vite dev
server proxies `/api` to `http://localhost:8000`.

## Frontend design system

The UI ports the look of a Figma Make export (kept locally, gitignored, never committed — see
`.gitignore`). Conventions to keep following:

- **Design tokens** live only in `frontend/src/index.css`, inside the Tailwind v4 `@theme` block
  (semantic names: `brand`, `accent`, `surface`, `surface-mint/lavender/coral`, `ink`, `muted`,
  `line`, `danger`, plus the `radius-sm/md/lg` and `shadow-card` scale). Components use the
  generated utilities (`bg-brand`, `rounded-lg`, `shadow-card`, …) — never raw hex values or
  inline styles for colors/radii.
- **Don't override a Button/Card variant's color classes via a trailing `className`** — Tailwind's
  utility order isn't guaranteed to match JSX string order, so two classes touching the same CSS
  property (e.g. a variant's `bg-brand` and an override's `bg-accent`) can silently pick either
  one. For a one-off color combo (e.g. a button on a dark background), write a small local
  `const onBrandButton = '...'` className string instead of fighting the shared variant — see
  `WelcomeBanner.tsx` or `Progress.tsx` for the pattern. `className` overrides are only safe for
  properties the base/variant never sets (margin, width, etc.).
- **Folder convention** (blueprint section 5): `app/` (router, layout, nav config), `components/`
  (generic, reusable: `Button`, `Card`, `Badge`, `StatCard`, `Sidebar`, `Header`...), `features/
  <name>/` (screen-specific: `dashboard`, `reader`, `vocabulary`, `review`, `progress` — note the
  flashcards route lives in the `review` folder, per blueprint naming), `mocks/` + `types/` for
  placeholder data.
- **Mocks are typed to match future API shapes.** Every screen's placeholder data lives in
  `src/mocks/<domain>.ts`, typed against `src/types/<domain>.ts`. When a real backend endpoint
  exists, swap the mock import for a TanStack Query call — components should not need to change,
  only where the data comes from.
- Several UI elements exist only visually right now, ahead of their backing MVP feature (streaks,
  daily reading-time goal, Progress screen analytics) — see the chat history / PR description for
  the running "beyond-MVP" list to revisit.

## Git hooks

Enforced via [pre-commit](https://pre-commit.com) (`.pre-commit-config.yaml`), not husky — this
is a polyglot repo (Python + Node) and pre-commit manages each hook's environment itself. A fresh
clone needs a one-time `uv tool install pre-commit && pre-commit install --install-hooks`.

- `commit-msg` hook rejects any commit message that isn't Conventional Commits (see allowed
  types/examples in the README's "Contributing" section). Merge and revert commits are exempt.
- `pre-commit` hook runs hygiene checks, `ruff` on `backend/`, `npm run lint` on `frontend/`, and
  `gitleaks` secret scanning — all scoped to be fast; the full test suites run in CI, not here.
- Hooks are local and bypassable (`--no-verify`) or simply not installed on someone's machine —
  CI must re-enforce the same checks as the real gate, hooks are just fast local feedback.

## Working rules

- Use Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, ...) — enforced by the `commit-msg`
  hook above.
- Write tests for new business logic (scheduler, offsets, ownership checks, validation) — not
  just for UI wiring.
- Don't add a dependency that isn't already in the blueprint's stack without asking first.
- Never commit secrets. `.env.example` documents required variables; real values stay in
  `.env`/`.env.local`, which are gitignored.
- Keep changes scoped to the step currently being worked on — don't jump ahead to later build-order
  steps (e.g. no database work while still on frontend scaffolding) unless asked.
