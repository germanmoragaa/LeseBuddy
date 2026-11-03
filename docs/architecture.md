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

On registration, the user is logged in immediately but must verify their email before using the
app: a 6-digit code (hashed, 15-minute expiry, 5-attempt cap) is emailed via `BackgroundTasks`,
and `POST /api/v1/auth/verify-email` checks it against `email_verification_codes`, setting
`users.email_verified_at`. `get_current_user` (any logged-in user — needed by auth, `/me`,
logout, and the verification endpoints themselves) stays separate from
`get_current_verified_user`, which additionally requires verification and 403s with
`{"code": "email_not_verified"}` otherwise; every real app endpoint depends on the latter. Full
reasoning (code vs. link, hashing, rate limiting, account-expiry rule, send-after-commit) is in
[docs/decisions/0002-email-verification.md](decisions/0002-email-verification.md).

On the frontend, `/`, `/login`, and `/signup` are public; `/verify-email` is wrapped in a
`RequireUnverifiedRoute` (logged-out → `/login`, already-verified → `/app`); everything under
`/app/*` is wrapped in a `ProtectedRoute` that redirects to `/login` (carrying the original path)
when `GET /api/v1/me` fails, or to `/verify-email` when logged in but unverified; a
`PublicOnlyRoute` sends already-logged-in users from the public pages to `/app` (or
`/verify-email` if unverified).

## Why this stack

FastAPI + Pydantic gives typed request/response validation for free, which matters for an API that also validates AI-generated output. PostgreSQL with explicit migrations keeps scheduling and ownership data auditable. React + TypeScript + Vite is a fast, well-understood baseline for an interactive reading UI. Keeping the LLM behind a provider interface avoids coupling the app to one vendor's API.
