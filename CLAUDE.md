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
- **NLP:** spaCy, `de_core_news_md` German model (pinned as a direct-URL dependency in
  `backend/pyproject.toml`'s `[tool.uv.sources]` — installed automatically by `uv sync`, no
  separate download step)
- **Translation & dictionary:** DeepL API (`deepl` Python SDK) for contextual machine
  translation; Wiktionary data via kaikki.org's extraction for grounded gender/plural/glosses
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

## Authentication

Server-side sessions over an `HttpOnly`/`SameSite=Lax` cookie, not JWTs — full reasoning in
[docs/decisions/0001-authentication.md](docs/decisions/0001-authentication.md). Key points for
future work:

- `app/api/deps.py`'s `get_current_user` is the dependency every authenticated route needs;
  health endpoints stay dependency-free and public.
- New env vars: `SESSION_COOKIE_SECURE` (false locally, must be true over https) and
  `SESSION_DURATION_DAYS` — both already have safe defaults in `app/core/config.py`.
- Frontend: `useCurrentUser()` (`src/hooks/useCurrentUser.ts`) is the single source of truth for
  "who's logged in," backed by `GET /api/v1/me`. A global 401 handler in `main.tsx`'s
  `QueryClient` nulls the cached user on any 401 — don't add per-component 401 handling, rely on
  that plus the route guards reacting to it.

## Email verification

Registered-but-unverified users can log in but can't use the app — full reasoning (code vs.
link, hashing, rate limiting, 24h unverified-account expiry, send-after-commit) in
[docs/decisions/0002-email-verification.md](docs/decisions/0002-email-verification.md). Key
points for future work:

- `email_verified_at` on `User` is nullable; `/api/v1/me`'s `email_verified` boolean derives
  from it. `app/api/deps.py`'s `get_current_verified_user` (wraps `get_current_user`, 403s with
  `{"code": "email_not_verified"}`) is the dependency every real app endpoint needs — plain
  `get_current_user` stays on auth endpoints, `/me`, logout, and the verification endpoints
  themselves, since unverified users must still be able to reach those.
- `app/services/auth_service.py`: `issue_verification_code` (cooldown + hourly cap,
  invalidate-then-insert) and `verify_email_code` (idempotent if already verified; expiry/attempt
  checks) are the two entry points. `_expire_stale_unverified_account` runs at the top of
  `register_user`, in the same transaction as the new insert — see the ADR before changing either.
- `username`/`email` uniqueness is enforced by functional `lower()` unique indexes at the
  database, not just the app-level pre-check — `register_user`'s `except IntegrityError` handles
  the race where two requests both pass the pre-check, and must keep mapping to the same
  field-specific 409, never a 500.
- Email sending goes through the `EmailSender` protocol (`app/services/email.py`):
  `SmtpEmailSender` (stdlib `smtplib`, points at Mailpit locally) in prod/dev,
  `FakeEmailSender` (in-memory `.sent` list) in tests via a `get_email_sender` dependency
  override. Never add a new email-sending dependency without checking this interface first.
- New env vars (`app/core/config.py`, all have safe local defaults): `SECRET_KEY` (keys the
  HMAC that hashes codes — **never commit a real value**), `SMTP_HOST`/`SMTP_PORT`/
  `SMTP_USERNAME`/`SMTP_PASSWORD`/`SMTP_USE_TLS`, `EMAIL_FROM`,
  `VERIFICATION_CODE_TTL_MINUTES`, `VERIFICATION_CODE_MAX_ATTEMPTS`,
  `VERIFICATION_RESEND_COOLDOWN_SECONDS`, `VERIFICATION_RESEND_HOURLY_CAP`,
  `UNVERIFIED_ACCOUNT_TTL_HOURS`.
- Frontend: `ProtectedRoute` redirects logged-in-but-unverified users to `/verify-email` instead
  of rendering `/app/*`; `PublicOnlyRoute` sends them to `/verify-email` instead of `/app`; a new
  `RequireUnverifiedRoute` guards `/verify-email` itself (logged-out → `/login`, already-verified
  → `/app`). Never log or display a verification code anywhere outside the user's own inbox
  (Mailpit locally stands in for that inbox).

## Articles and the reading workspace

Full reasoning (model choice, offset contract, separable-verb detection and limits, analysis
versioning, why morphology is "detected" not "verified") is in
[docs/decisions/0003-nlp-pipeline.md](docs/decisions/0003-nlp-pipeline.md). Key points for
future work:

- `app/services/nlp/` is the only place that imports `spacy` — everything else depends on
  `app/services/nlp/types.py`'s plain `Token`/`Sentence`/`SeparableVerb`/`AnalysisResult`
  models. Don't leak a spaCy object past `app/services/nlp/analyze.py`.
- Offsets are Unicode **code points** into the stored, NFC-normalized `original_text` — never
  UTF-16. The frontend converts once per article via `src/lib/textOffsets.ts`'s
  `CodePointIndex`; nothing may call `.slice()`/`.substring()` on `original_text` with a raw
  backend offset directly. `unicodedata.normalize("NFC", ...)` happens in exactly one place,
  `app/services/article_service.py`'s `create_article` — don't add a second normalization call
  site.
- `app/services/analysis_service.py`'s `CURRENT_ANALYSIS_VERSION` constant gates
  `article_analyses`: bump it by hand when the pipeline logic or model changes, never edit a
  stored row in place. `get_or_create_analysis` computes off-database before inserting and
  handles the concurrent-request race the same way `auth_service.register_user` handles the
  username/email race (`except IntegrityError` → re-fetch).
- `backend/scripts/seed_articles.py` (`uv run python -m scripts.seed_articles <email>`) seeds
  a few original German texts for local dev — the target user must already exist.
- Frontend: `features/reader/useTokenSelection.ts` is the single source of truth for the
  roving-tabindex cursor *and* multi-word selection — both only ever move between word tokens
  (`!is_punct && !is_space`), so don't add a second, independent "which word is focused"
  concept.

## Translations, dictionary, and vocabulary

Word meanings come from DeepL (contextual translation) and Wiktionary data (grounded
gender/plural/glosses) instead of a paid LLM — full reasoning (why not an LLM, cache-key design,
quota protection, dataset choice, source labeling, license) in
[docs/decisions/0004-translations-and-dictionary.md](docs/decisions/0004-translations-and-dictionary.md).
Key points for future work:

- `app/services/translation/provider.py`'s `TranslationProvider` Protocol
  (`DeepLTranslationProvider` in prod, `FakeTranslationProvider` in tests via a
  `get_translation_provider` dependency override, `NullTranslationProvider` when
  `DEEPL_API_KEY` is empty) is the only seam translation code should go through — don't call
  the `deepl` SDK directly outside `deepl_provider.py`.
- `app/services/selection.py`'s `resolve_selection` is shared by `/translate`, `/dictionary`,
  and vocabulary save — it validates `{start, end}` against the article's own stored token
  boundaries and derives the sentence context server-side. Never add a second
  offset-validation implementation; never accept a context string from the client.
- `translation_cache` is keyed by a single hash of `(source_text, context, target_lang,
  provider)` — deliberately excludes the user, since the same word+sentence translates
  identically for everyone. `translation_request_log` counts only non-cached provider calls
  for the per-user hourly rate limit.
- `dictionary_entries`/`dictionary_forms` are populated by
  `uv run python -m app.scripts.import_dictionary` (streams a kaikki.org dump, replaces the
  tables in one transaction) — never commit the raw downloaded dump (`.gitignore`'d). Gender is
  normalized to spaCy's `Masc`/`Fem`/`Neut` codes **at import time**, not at lookup time.
  `dictionary_service.resolve_dictionary_entry` returns `None` on no match — never guess.
- Frontend: `WordDetailPanel.tsx` fires the dictionary and word-translation queries in parallel
  on every word click (each with its own loading/error state); `Reader.tsx`'s
  `translationDisabled` state is lifted above the panel so a not-configured/quota error stops
  auto-firing translation for the rest of the session, not just the current selection.
  `grammarLabels.ts`'s `resolveGender` is the one place gender-disagreement is resolved
  (dictionary wins) — don't duplicate that logic elsewhere.
- `POST /api/v1/vocabulary` accepts only `{article_id, start, end}` — the backend re-derives and
  snapshots everything else (never trust a client-sent lemma/translation/grammar payload).
  Dedup key is `(user_id, lower(lemma_or_expression))`; heteronym collisions are a known,
  accepted limitation (see the ADR), not a bug to silently fix by widening the key.
- New env vars (`app/core/config.py`, all have safe local defaults): `DEEPL_API_KEY`
  (**required for translation to work; never commit a real value**),
  `TRANSLATION_DEFAULT_LANGUAGE`, `TRANSLATION_RATE_LIMIT_PER_HOUR`,
  `TRANSLATION_USAGE_CHECK_INTERVAL_SECONDS`, `TRANSLATION_USAGE_WARN_THRESHOLD`.

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
- **Folder convention** (blueprint section 5, extended as needed): `app/` (router, layout, nav
  config, route guards), `components/` (generic, reusable: `Button`, `Card`, `Badge`, `StatCard`,
  `Sidebar`, `Header`...), `features/<name>/` (screen-specific: `dashboard`, `reader`,
  `vocabulary`, `review`, `progress`, `auth` — note the flashcards route lives in the `review`
  folder, per blueprint naming), `hooks/` (shared React hooks like `useCurrentUser`), `mocks/` +
  `types/` for placeholder data.
- **Mocks are typed to match future API shapes — swapped for real calls as each backend
  endpoint lands.** Dashboard stats, flashcards, and progress are still `src/mocks/<domain>.ts`,
  typed against `src/types/<domain>.ts`; swap each for a TanStack Query call as its backend
  endpoint lands, without touching the components. Three exceptions so far: user identity
  (`Sidebar`'s account card, `Home`'s greeting) comes from `useCurrentUser()`, not
  `mocks/dashboard.ts`; the reader (`src/features/reader/`) is fully real now —
  `mocks/reader.ts`/`types/reader.ts` were deleted, don't reintroduce them; and vocabulary
  (`src/features/vocabulary/`) is fully real now too — `mocks/vocabulary.ts` and the SRS-only
  `StatusBadge` component were deleted, don't reintroduce either (no `flashcards` table exists
  yet, so there's nothing real to back review-status fields). The dashboard's "Continue
  reading" card and "Recent reading" list still link to `/app/reader/new` rather than a real
  article id, since they're still mock-backed.
- Several UI elements exist only visually right now, ahead of their backing MVP feature (streaks,
  daily reading-time goal, Progress screen analytics) — see the chat history / PR description for
  the running "beyond-MVP" list to revisit.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every pull request and every push to `main`,
in three parallel jobs: `backend` (ruff check/format, `alembic upgrade head` against a Postgres
18 service container, pytest), `frontend` (lint, typecheck, test, build), `quality` (pre-commit
on all files, plus — on pull requests only — a Conventional Commits check on the PR title, since
PRs are squash-merged and the title becomes the commit message on `main`).

This is the real gate, not the pre-commit hooks — hooks are local and bypassable, CI is not.
**All three jobs must pass before a PR can be merged** (enforced via branch protection on
`main`).

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
