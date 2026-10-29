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

- **Frontend:** React + TypeScript + Vite, Tailwind CSS, TanStack Query
- **Backend:** Python + FastAPI, Pydantic
- **Database:** PostgreSQL with SQLAlchemy + Alembic (not set up yet)
- **NLP:** spaCy German model (not set up yet)
- **AI:** LLM behind a provider interface (not set up yet)
- **Testing:** pytest (backend), Vitest + React Testing Library (frontend), Playwright (e2e, not
  set up yet)

## Running things

### Backend (`backend/`)

```bash
cd backend
uv run fastapi dev app/main.py   # dev server, http://localhost:8000
uv run pytest                     # tests
uv run ruff check .               # lint
```

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

## Working rules

- Use Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, ...).
- Write tests for new business logic (scheduler, offsets, ownership checks, validation) — not
  just for UI wiring.
- Don't add a dependency that isn't already in the blueprint's stack without asking first.
- Never commit secrets. `.env.example` documents required variables; real values stay in
  `.env`/`.env.local`, which are gitignored.
- Keep changes scoped to the step currently being worked on — don't jump ahead to later build-order
  steps (e.g. no database work while still on frontend scaffolding) unless asked.
