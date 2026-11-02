# LeseBuddy

[![CI](https://github.com/germanmoragaa/LeseBuddy/actions/workflows/ci.yml/badge.svg)](https://github.com/germanmoragaa/LeseBuddy/actions/workflows/ci.yml)

*Read authentic German. Understand more. Remember what you learn.*

German learners who read real-world texts constantly hit words and expressions they don't know, and dictionary lookups strip away the context that made the meaning clear in the first place. LeseBuddy lets learners paste a German text, see a difficulty estimate, and get contextual explanations for the words and expressions they select — then turns saved vocabulary into spaced-repetition flashcards so it's actually remembered.

## Tech stack

- **Frontend:** React + TypeScript + Vite, Tailwind CSS, TanStack Query
- **Backend:** Python + FastAPI, Pydantic
- **Database:** PostgreSQL with SQLAlchemy + Alembic
- **NLP:** spaCy (German model)
- **AI:** LLM behind a provider interface
- **Testing:** pytest, Vitest + React Testing Library, Playwright
- **Infra:** Docker Compose, GitHub Actions CI

See [docs/architecture.md](docs/architecture.md) and [docs/blueprint.md](docs/blueprint.md) for details.

## Local development

```bash
docker compose up -d   # Postgres 18, creates both lesebuddy and lesebuddy_test databases

cd backend
cp .env.example .env            # optional — defaults already match docker-compose.yml
uv run alembic upgrade head      # apply migrations
uv run fastapi dev app/main.py   # http://localhost:8000
uv run pytest                    # backend tests (uses lesebuddy_test, never the dev DB)
uv run ruff check .              # lint

cd ../frontend
npm run dev   # http://localhost:5173, proxies /api to localhost:8000
npm test
```

After changing SQLAlchemy models, generate and review a migration before committing it:

```bash
uv run alembic revision --autogenerate -m "describe the change"
```

### Authentication

Accounts use server-side sessions over an `HttpOnly` cookie — see
[docs/architecture.md](docs/architecture.md#authentication) and
[the ADR](docs/decisions/0001-authentication.md) for the full reasoning. To try it locally:

- In the app: go to `http://localhost:5173/signup`, create an account, and you're taken straight
  into `/app` (already logged in). Log out from the sidebar's "…" menu.
- Via the API directly:
  ```bash
  curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d '{"username": "alex_morgan", "email": "alex@example.com", "password": "correct horse battery staple"}'

  curl -b cookies.txt http://localhost:8000/api/v1/me
  ```

Backend env vars for this (see `backend/.env.example`, both already have safe local defaults):
`SESSION_COOKIE_SECURE` (set `true` once served over https) and `SESSION_DURATION_DAYS`.

## Contributing

### Git hooks

This repo uses [pre-commit](https://pre-commit.com) to enforce commit hygiene locally. After
cloning:

```bash
uv tool install pre-commit
pre-commit install --install-hooks
```

This installs two hook types:

- **`pre-commit`** — trailing-whitespace/EOF/YAML/TOML hygiene, `ruff` lint+format on
  `backend/`, `npm run lint` on `frontend/`, and `gitleaks` secret scanning.
- **`commit-msg`** — rejects commit messages that don't follow
  [Conventional Commits](https://www.conventionalcommits.org).

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`,
`revert`. Scope is optional, and breaking changes use `!` before the colon. Examples:

```
feat(reader): add text-selection highlighting
fix: correct offset calculation for umlauts
docs: update architecture notes
feat!: change vocabulary API response shape
```

Merge commits and `git revert`'s default commit messages are not blocked by this check.

To run all checks manually without committing:

```bash
pre-commit run --all-files
```

## Status: 🚧 in development
