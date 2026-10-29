# LeseBuddy

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
