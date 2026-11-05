# LeseBuddy

[![CI](https://github.com/germanmoragaa/LeseBuddy/actions/workflows/ci.yml/badge.svg)](https://github.com/germanmoragaa/LeseBuddy/actions/workflows/ci.yml)

*Read authentic German. Understand more. Remember what you learn.*

German learners who read real-world texts constantly hit words and expressions they don't know, and dictionary lookups strip away the context that made the meaning clear in the first place. LeseBuddy lets learners paste a German text, see a difficulty estimate, and get contextual explanations for the words and expressions they select — then turns saved vocabulary into spaced-repetition flashcards so it's actually remembered.

## Tech stack

- **Frontend:** React + TypeScript + Vite, Tailwind CSS, TanStack Query
- **Backend:** Python + FastAPI, Pydantic
- **Database:** PostgreSQL with SQLAlchemy + Alembic
- **NLP:** spaCy (`de_core_news_md` German model)
- **Translation & dictionary:** DeepL API (contextual machine translation), Wiktionary data via
  kaikki.org (grounded gender/plural/glosses)
- **AI:** LLM behind a provider interface
- **Testing:** pytest, Vitest + React Testing Library, Playwright
- **Infra:** Docker Compose, GitHub Actions CI

See [docs/architecture.md](docs/architecture.md) and [docs/blueprint.md](docs/blueprint.md) for details.

## Local development

```bash
docker compose up -d   # Postgres 18 (both lesebuddy and lesebuddy_test databases) + Mailpit

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

### Email verification

After signup, the user is logged in but redirected to `/verify-email` and must enter a 6-digit
code before using the app. See [docs/architecture.md](docs/architecture.md#authentication) and
[the ADR](docs/decisions/0002-email-verification.md) for the full reasoning. To try it locally:

- `docker compose up -d` also starts [Mailpit](https://github.com/axllent/mailpit), a fake SMTP
  server. After registering, open **http://localhost:8025** to see the code in the email that
  was "sent" — nothing leaves your machine.
- Codes expire after 15 minutes and allow 5 attempts; "Resend code" is rate-limited (60s
  cooldown, 5/hour).
- Tests never touch Mailpit or any real SMTP server — they use an in-memory fake sender
  (`app/services/email.py`'s `FakeEmailSender`).

Backend env vars for this (see `backend/.env.example`, all have safe local defaults pointing at
Mailpit): `SECRET_KEY` (**must** be overridden with a real random value outside local dev —
never commit a real one), `SMTP_HOST`/`SMTP_PORT`/`SMTP_USERNAME`/`SMTP_PASSWORD`/`SMTP_USE_TLS`,
`EMAIL_FROM`, `VERIFICATION_CODE_TTL_MINUTES`, `VERIFICATION_CODE_MAX_ATTEMPTS`,
`VERIFICATION_RESEND_COOLDOWN_SECONDS`, `VERIFICATION_RESEND_HOURLY_CAP`,
`UNVERIFIED_ACCOUNT_TTL_HOURS`.

### Reading workspace & German NLP

Articles are saved and analyzed with [spaCy](https://spacy.io) (`de_core_news_md`) — tokens,
lemmas, part-of-speech tags, detected morphology, sentence boundaries, and separable-verb
detection (e.g. "rufe ... an" → "anrufen"). See
[docs/architecture.md](docs/architecture.md#articles-and-the-reading-workspace) and
[the ADR](docs/decisions/0003-nlp-pipeline.md) for the full reasoning, including the offset
contract and known limitations.

- The German model is a pinned dependency (`backend/pyproject.toml`'s `[tool.uv.sources]`) —
  `uv sync` installs it automatically, no separate `spacy download` step.
- Seed a few short, original German texts for local dev (the target user must already exist):
  ```bash
  cd backend
  uv run python -m scripts.seed_articles you@example.com
  ```
- Run just the NLP tests: `uv run pytest tests/test_nlp_analyze.py tests/test_analysis.py`.
- An article's analysis is computed once and cached (`article_analyses`); open it again and
  it's served from the stored row, not recomputed.

### Contextual translation, dictionary, and vocabulary

Word meanings come from two free sources instead of a paid LLM: [DeepL](https://www.deepl.com)
(contextual machine translation) and [Wiktionary](https://www.wiktionary.org) via
[kaikki.org](https://kaikki.org)'s machine-readable extraction (grounded gender/plural/glosses).
See [docs/architecture.md](docs/architecture.md#contextual-translation-dictionary-data-and-vocabulary)
and [the ADR](docs/decisions/0004-translations-and-dictionary.md) for the full reasoning.

- **Dictionary data is [CC BY-SA](https://creativecommons.org/licenses/by-sa/3.0/) licensed** —
  every place it renders in the app shows a Wiktionary attribution line, per the license's
  share-alike requirement.
- Import the dictionary (streams a gzip dump, never loads it fully into memory, replaces the
  tables in one transaction):
  ```bash
  cd backend
  uv run python -m app.scripts.import_dictionary
  ```
  CI never runs this against the real dataset — `tests/fixtures/dictionary/sample.jsonl` is a
  small fixture in the real kaikki line format.
- Click a word in the reader to see its dictionary entry (free, instant) and a contextual
  translation (quota-limited, cached — the same word in the same sentence is never
  re-translated); "Translate sentence" is a separate, on-request action to save characters.
- "Save to vocabulary" snapshots the dictionary/translation data the user already saw into a
  personal, deduplicated vocabulary list at `/app/vocabulary` — saved items never depend on the
  dictionary or translation cache staying unchanged, and deleting an article never deletes the
  vocabulary saved from it.
- A manual (not-CI) evaluation script runs ~15 real selections from the seeded article through
  the real DeepL + dictionary and writes a markdown report:
  ```bash
  uv run python -m app.scripts.eval_translation_dictionary
  ```

Backend env vars for this (see `backend/.env.example`): `DEEPL_API_KEY` (**required** for
translation to work — the app still starts without it, returning a clear "not configured" error
instead; never commit a real value), `TRANSLATION_DEFAULT_LANGUAGE`,
`TRANSLATION_RATE_LIMIT_PER_HOUR`, `TRANSLATION_USAGE_CHECK_INTERVAL_SECONDS`,
`TRANSLATION_USAGE_WARN_THRESHOLD`.

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
