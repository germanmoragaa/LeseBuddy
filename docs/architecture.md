# Architecture

LeseBuddy has three components:

- **Frontend** — React + TypeScript (Vite), responsible for the reading workspace, vocabulary library, and flashcard review UI.
- **Backend** — Python + FastAPI, a typed REST API that owns business logic: text analysis, AI explanations, the spaced-repetition scheduler, and data ownership checks.
- **Database** — PostgreSQL, the durable store for articles, vocabulary, flashcards, and review logs, accessed through SQLAlchemy with Alembic migrations.

## Communication

The frontend talks to the backend exclusively over REST under a versioned prefix, `/api/v1`. Versioning the prefix lets the API evolve without breaking existing clients. The backend is the only component that talks to PostgreSQL and to the LLM provider.

## Authentication

Sessions are server-side, not JWTs: on register/login the backend creates a row in `sessions`
(user_id, a sha256 hash of a random token, `expires_at`, `last_used_at`) and sends the raw token
to the browser as an `HttpOnly`, `SameSite=Lax` cookie. The frontend never reads or stores the
token itself — it only ever asks `GET /api/v1/me` who's logged in. Every authenticated route
depends on `get_current_user` (`app/api/deps.py`), which reads that cookie, loads and validates
the session, bumps `last_used_at`, and raises 401 otherwise; health endpoints stay dependency-free
and public. Full reasoning (hashing, password policy, cookies, CSRF, brute-force, trade-offs) is
in [docs/decisions/0001-authentication.md](decisions/0001-authentication.md).

On the frontend, `/`, `/login`, and `/signup` are public; everything under `/app/*` is wrapped in
a `ProtectedRoute` that redirects to `/login` (carrying the original path) when `GET /api/v1/me`
fails, and a `PublicOnlyRoute` sends already-logged-in users from the public pages to `/app`.

## Why this stack

FastAPI + Pydantic gives typed request/response validation for free, which matters for an API that also validates AI-generated output. PostgreSQL with explicit migrations keeps scheduling and ownership data auditable. React + TypeScript + Vite is a fast, well-understood baseline for an interactive reading UI. Keeping the LLM behind a provider interface avoids coupling the app to one vendor's API.
