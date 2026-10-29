# Architecture

LeseBuddy has three components:

- **Frontend** — React + TypeScript (Vite), responsible for the reading workspace, vocabulary library, and flashcard review UI.
- **Backend** — Python + FastAPI, a typed REST API that owns business logic: text analysis, AI explanations, the spaced-repetition scheduler, and data ownership checks.
- **Database** — PostgreSQL, the durable store for articles, vocabulary, flashcards, and review logs, accessed through SQLAlchemy with Alembic migrations.

## Communication

The frontend talks to the backend exclusively over REST under a versioned prefix, `/api/v1`. Versioning the prefix lets the API evolve without breaking existing clients. The backend is the only component that talks to PostgreSQL and to the LLM provider.

## Why this stack

FastAPI + Pydantic gives typed request/response validation for free, which matters for an API that also validates AI-generated output. PostgreSQL with explicit migrations keeps scheduling and ownership data auditable. React + TypeScript + Vite is a fast, well-understood baseline for an interactive reading UI. Keeping the LLM behind a provider interface avoids coupling the app to one vendor's API.
