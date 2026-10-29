# LeseBuddy — Product & Engineering Blueprint

> A portfolio-ready web app for German learners who want to read authentic texts, understand unfamiliar language in context, and remember useful vocabulary.
>
> **Product promise:** *Read authentic German. Understand more. Remember what you learn.*

## 1. Product concept

**LeseBuddy** is a web application for learners of German, initially focused on people around **B1 level who want to progress toward B2**.

Users paste or save a German article or text. The app estimates its difficulty, lets learners inspect words and expressions in context, provides translations and explanations, and turns selected vocabulary into flashcards with spaced repetition. A progress dashboard helps learners see what they have studied and what needs review.

### Core user journey

1. Paste or save a German text.
2. See a preliminary estimate of its difficulty.
3. Read the text and select an unfamiliar word or expression.
4. Review its contextual translation, meaning, and relevant grammar information.
5. Save it to a personal vocabulary library.
6. Review saved items through flashcards.
7. Track learning activity and upcoming reviews.

### Primary persona

- A B1 German learner who wants to become more comfortable reading real-world German and move toward B2.
- Wants explanations that fit the sentence, rather than isolated dictionary translations.
- Wants a low-friction way to turn reading into vocabulary practice.

## 2. MVP scope

### Include in the MVP

- Paste and save German text.
- A preliminary text-difficulty estimate.
- A reading workspace with selectable words and expressions.
- Context-aware explanations and translations.
- Vocabulary library with saved words and example context.
- Flashcards with spaced repetition.
- Basic progress analytics.
- Automated tests, CI, documentation, and a demonstrable deployment.

### Defer until later

- Claims of official or certified CEFR assessment.
- Speech recognition, pronunciation scoring, or audio features.
- Browser extension and native mobile applications.
- Advanced predictive machine learning.
- Elaborate social features or gamification.
- Automatically generating explanations for every word in a text.

**Scope rule:** First deliver one complete end-to-end workflow that works reliably. Add breadth only after the core journey is usable and tested.

## 3. Suggested application screens

### A. Dashboard

Show:
- Vocabulary items saved.
- Reviews completed.
- Cards due today.
- Recent activity.
- A simple learning-progress view.
- A small, explainable recommendation such as “Review 8 cards due today.”

### B. Reading workspace

Show:
- The saved or pasted German text.
- A visible, preliminary difficulty estimate.
- Selectable words and expressions.
- Contextual meaning, translation, part of speech, and relevant grammar information when available.
- A “Save to vocabulary” action.
- Clear loading, error, and empty states.

### C. Vocabulary library

Show:
- Saved words and expressions.
- Meaning and translation.
- Example sentence or source context.
- Part of speech and grammar metadata when available.
- Search, filtering, and editing.
- A way to create or access a flashcard.

### D. Flashcard review

Show:
- A prompt (for example, a German word or expression).
- A way to reveal its meaning or example.
- Self-assessment options: **Again, Hard, Good, Easy**.
- The next review date or a clear indication of the scheduling result.

## 4. Recommended technology stack

| Area | Suggested technology | Purpose |
|---|---|---|
| Frontend | React + TypeScript + Vite | Fast, maintainable web UI |
| Styling | Tailwind CSS | Consistent UI styling |
| Server-state management | TanStack Query | API requests, caching, loading/error states |
| Backend | Python + FastAPI | Typed, documented REST API |
| Validation | Pydantic | Request/response and AI-output validation |
| Database | PostgreSQL | Durable relational data |
| ORM and migrations | SQLAlchemy + Alembic | Database access and schema evolution |
| German NLP | spaCy with a German model | Tokenization, lemmas, part-of-speech tags, spans |
| AI explanations | LLM behind a provider interface | Context-aware explanations |
| Backend tests | pytest | Unit and integration tests |
| Frontend tests | Vitest + React Testing Library | Component and frontend logic tests |
| End-to-end tests | Playwright | Test the user journey in a browser |
| Local services | Docker Compose | Reproducible development setup |
| CI | GitHub Actions | Automated checks on changes |

Keep the LLM behind a small provider interface so the rest of the application does not depend on one vendor's API.

## 5. Suggested repository structure

```text
lesebuddy/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── reader/
│   │   │   ├── vocabulary/
│   │   │   ├── review/
│   │   │   └── dashboard/
│   │   ├── lib/
│   │   └── types/
│   ├── tests/
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   └── services/
│   │       ├── nlp/
│   │       ├── ai/
│   │       └── scheduler/
│   ├── migrations/
│   ├── tests/
│   └── pyproject.toml
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── decisions/
├── .github/
│   └── workflows/
├── .env.example
├── docker-compose.yml
├── .gitignore
└── README.md
```

Treat this as a starting point, not a requirement to create every directory on day one. Add folders as the code needs them.

## 6. API outline

Use a versioned prefix such as `/api/v1`.

| Resource | Example endpoints | Responsibility |
|---|---|---|
| Authentication and user | `POST /auth/...`, `GET /me` | Sign-in/session and current-user information |
| Articles | `POST /articles`, `GET /articles`, `GET /articles/{id}`, `POST /articles/{id}/analyze`, `DELETE /articles/{id}` | Save, retrieve, analyze, and delete texts |
| Vocabulary | `POST /vocabulary`, `GET /vocabulary`, `GET /vocabulary/{id}`, `PATCH /vocabulary/{id}`, `DELETE /vocabulary/{id}`, `POST /vocabulary/{id}/explain` | Manage saved vocabulary and explanations |
| Flashcards | `POST /flashcards`, `GET /flashcards/due`, `PATCH /flashcards/{id}` | Create cards and retrieve/update scheduling state |
| Reviews | `POST /reviews`, `GET /reviews/summary` | Record review events and return review summaries |
| Export | `GET /export/anki` | Export vocabulary/cards for Anki |
| Analytics | `GET /analytics/overview`, `GET /analytics/reviews`, `GET /analytics/vocabulary` | Dashboard and learning activity |
| Recommendations | `GET /recommendations` | Simple, explainable next-step suggestions |

Authentication can be simplified for a first local prototype, but if the app supports multiple users, enforce ownership checks for every user-specific resource. Never rely on a client-supplied user ID as proof of access.

## 7. Data model

Use UUIDs for identifiers, foreign keys, constraints, and migrations. Index fields used frequently for filtering and retrieval.

### `users`

- `id`
- `email` (unique, if email-based accounts are used)
- `password_hash` only if implementing password authentication
- `created_at`

### `articles`

- `id`
- `user_id`
- `title` (optional)
- `source_url` (optional)
- `original_text`
- `language`
- `created_at`
- `updated_at`

Preserve the original text so later analyses can be compared and offsets can be checked against the original content.

### `article_analyses`

- `id`
- `article_id`
- `analysis_version`
- `difficulty_estimate`
- `difficulty_details` (JSONB)
- `created_at`

Store analyses separately and version them so the app can change its analysis logic without silently overwriting history.

### `vocabulary_items`

- `id`
- `user_id`
- `lemma`
- `display_form`
- `meaning`
- `translation`
- `part_of_speech` (nullable)
- `grammar_metadata` (JSONB, nullable)
- `created_at`
- `updated_at`

Do not assume every item is a single word: useful expressions and multi-word phrases should be supported.

### `article_vocabulary`

Connect vocabulary items to their source context.

- `id`
- `article_id`
- `vocabulary_item_id`
- `start_offset`
- `end_offset`
- `context_text`
- `created_at`

**Important:** One vocabulary item may occur multiple times in a text. Keep occurrence/context records separate from the canonical vocabulary item. Define offsets consistently (for example, Unicode code-point offsets) and test them against German characters and punctuation.

### `flashcards`

- `id`
- `user_id`
- `vocabulary_item_id`
- `due_at`
- `interval_days`
- `ease_factor`
- `repetition_count`
- `last_reviewed_at`
- `created_at`
- `updated_at`

Store scheduling state explicitly. This makes due-card queries and scheduling changes easier to inspect and test.

### `review_logs`

- `id`
- `user_id`
- `flashcard_id`
- `rating` (`again`, `hard`, `good`, or `easy`)
- `reviewed_at`
- `previous_due_at` (optional)
- `next_due_at` (optional)
- `interval_days_after` (optional)

Treat review logs as append-only events. They provide the history needed for analytics and debugging.

### Data-integrity rules

- Every user-owned record must be scoped to its owner.
- Use foreign keys and suitable deletion behavior.
- Decide explicitly what happens to vocabulary if an article is deleted; ideally preserve the user's canonical vocabulary while removing or detaching article-occurrence records.
- Prevent accidental duplicate cards for the same vocabulary item if that is the intended product rule.
- Add indexes for `user_id`, `due_at`, foreign keys, and common search/filter fields.
- Keep migrations committed to version control.

## 8. German NLP and AI pipeline

### Suggested pipeline

1. Validate the submitted text and apply conservative normalization.
2. Process it with spaCy's German model.
3. Extract tokens, lemmas, part-of-speech tags, and character spans.
4. Calculate a preliminary difficulty estimate using transparent baseline features.
5. When a learner selects a word or expression, request a contextual explanation.
6. Validate the AI response against a Pydantic schema.
7. Save selected vocabulary and the relevant source context.
8. Keep a clear distinction between AI-generated content and verified dictionary data.

### Difficulty estimate

Start with a transparent heuristic rather than a model that is difficult to explain. Potential features include:
- Average sentence length.
- Word length and frequency, if a suitable frequency list is available.
- Proportion of unknown or uncommon lemmas, if the app has a defensible vocabulary list.
- Clause or syntactic complexity, if reliably available.

Treat the output as a **rough estimate**, not an official CEFR classification. Explain uncertainty in the UI and evaluate the heuristic on a manually reviewed set of texts before making strong claims.

### Context-aware explanation

Request only the explanation the learner needs for a selected word or expression, rather than generating explanations for every word in the article.

Possible structured fields:
- Selected expression.
- Lemma or base form.
- Contextual meaning in this sentence.
- Translation into the learner's preferred language.
- Part of speech.
- Relevant grammar notes.
- One short example, if useful.
- Confidence or uncertainty indicator.
- Whether the data is AI-generated or dictionary-verified.

Do not invent grammatical gender, plural forms, or other morphology when uncertain. Where possible, ground dictionary-style facts in a reliable lexical source and distinguish those facts from model-generated interpretations.

### Text offsets

- Define whether spans use Unicode code points or another consistent convention.
- Preserve the source text used to calculate spans.
- Test punctuation, umlauts, `ß`, curly quotes, line breaks, and repeated occurrences.
- Avoid modifying whitespace or Unicode characters after calculating offsets unless offsets are recalculated.

## 9. Spaced-repetition scheduler

Implement the scheduler as a **pure, deterministic Python function** with explicit inputs and outputs. Use a documented SM-2-style algorithm or another clearly explained scheduling approach.

Review ratings:
- **Again** — the learner could not recall the item.
- **Hard** — recall was difficult.
- **Good** — recall was successful with normal effort.
- **Easy** — recall was very easy.

The backend should calculate the next interval and due date; do not trust a client to choose its own schedule. When a review is submitted, use a database transaction to append a `review_logs` event and update the flashcard's scheduling state together.

Test the scheduler with fixed dates and edge cases. Make the interval/ease-factor rules understandable in the documentation.

## 10. Analytics and recommendations

Useful MVP metrics:
- Number of saved vocabulary items.
- Number of reviews completed.
- Number of cards due today.
- Recent activity over time.
- Review ratings distribution.
- A simple count of items that need another review.
- Explainable recommendations based on due cards or recently saved vocabulary.

Be precise with terminology: a rate derived from self-reported review ratings is not a direct measurement of long-term retention. Label it as a review success rate or similar, rather than claiming to measure actual recall or mastery.

## 11. Testing strategy

### Unit tests

- Scheduler intervals and due dates.
- Text offsets and repeated occurrences.
- Difficulty-feature calculations.
- Pydantic request/response validation.
- Analytics calculations.
- Text normalization behavior.

### Integration tests

- Article create/read/update/delete flows.
- Vocabulary create/read/update/delete flows.
- Review submission updates the card and adds a review log.
- User A cannot access User B's articles, vocabulary, or cards.
- Article deletion preserves canonical vocabulary according to the chosen deletion policy.

### NLP and AI evaluation

- Build a small, manually reviewed collection of German texts and selected terms.
- Check tokenization, lemmas, and offsets against expected results.
- Review explanation quality for contextual meaning and grammar claims.
- Track known failure cases instead of treating every AI response as correct.

### End-to-end test

At minimum, automate the core journey:
1. Paste and save a German text.
2. Select a word or expression.
3. Request an explanation.
4. Save it to vocabulary.
5. Review its flashcard and choose a rating.
6. Confirm that the dashboard or due date reflects the review.

### Quality targets

Aim for meaningful coverage of core business logic (for example, around 80% as an initial target), but do not treat a coverage percentage as proof of correctness. Prioritize high-risk behavior, data ownership, and scheduling edge cases.

## 12. GitHub issue backlog

Use these as initial issues. Keep each issue small enough to finish and review independently.

### P0 — Core MVP

1. **Document product requirements and architecture**
   - Add the problem statement, target user, MVP boundaries, core user journey, and architecture decisions.
2. **Scaffold frontend and backend**
   - Create React/TypeScript/Vite frontend and FastAPI backend with health endpoints.
3. **Add PostgreSQL and migrations**
   - Configure local database, SQLAlchemy models, and Alembic migration workflow.
4. **Set up CI**
   - Run backend tests, frontend tests, and lint/type checks in GitHub Actions.
5. **Implement article persistence**
   - Save, list, retrieve, and delete user-owned articles.
6. **Build the reading workspace**
   - Render text and support selecting words/expressions with accurate spans.
7. **Add German NLP**
   - Integrate spaCy German tokenization, lemmas, POS, and spans.
8. **Add contextual AI explanations**
   - Create provider interface, structured response schema, error handling, and tests.
9. **Implement vocabulary management**
   - Save, search/list, edit, and delete vocabulary items.
10. **Implement spaced repetition**
    - Add deterministic scheduler, due-card endpoint, and append-only review logging.
11. **Build flashcard review UI**
    - Reveal answer and submit Again/Hard/Good/Easy ratings.
12. **Add basic analytics**
    - Show saved vocabulary, review counts, due cards, and activity.
13. **Automate the core user journey**
    - Add Playwright end-to-end test and document how to run it.

### P1 — Portfolio polish

14. **Create and evaluate a difficulty-estimation baseline**
    - Document features, limitations, and a manually reviewed evaluation set.
15. **Add Anki export**
    - Export vocabulary and useful context in a documented format.
16. **Add rule-based recommendations**
    - Recommend due cards or recently saved items with explainable rules.
17. **Deploy and polish the portfolio presentation**
    - Add demo data, screenshots, architecture documentation, setup instructions, and a short demo video or GIF.

## 13. Suggested six-week roadmap

Assumption: approximately **8–12 hours per week**. Adjust based on available time and the complexity of integration work.

| Week | Focus | Deliverable |
|---|---|---|
| 1 | Repository, architecture notes, frontend/backend scaffolding, database, CI | Running skeleton with automated checks |
| 2 | Article persistence, reader UI, text spans, spaCy | Read and inspect a saved German text |
| 3 | Contextual explanations and vocabulary library | Save an explained word or phrase |
| 4 | Flashcards, scheduler, review logs, basic analytics, tests | Complete end-to-end learning loop |
| 5 | Difficulty-estimation baseline, Anki export, recommendations | More polished feature set |
| 6 | Deployment, README, screenshots, demo, cleanup | Portfolio-ready public project |

The main milestone is the end-to-end workflow, not the number of features. If time is limited, reduce P1 work before compromising correctness, security, or tests in the core workflow.

## 14. Definition of done for the MVP

A user can:

- [ ] Paste and save a German text.
- [ ] See a clearly labeled preliminary difficulty estimate.
- [ ] Select a word or expression in context.
- [ ] Get a contextual explanation and translation.
- [ ] Save the item to a vocabulary library with its source context.
- [ ] Review it as a flashcard.
- [ ] Submit a review rating and receive a calculated next due date.
- [ ] See updated learning metrics on the dashboard.

Engineering requirements:
- [ ] Core backend logic has unit tests.
- [ ] Database changes use migrations.
- [ ] User-owned resources have ownership checks if accounts are enabled.
- [ ] AI output is validated and errors are handled.
- [ ] Secrets are not committed; `.env.example` documents required variables.
- [ ] CI runs the relevant tests and checks.
- [ ] README explains setup, architecture, testing, limitations, and demo access.

## 15. Portfolio and LinkedIn positioning

The project is stronger as a portfolio piece when it demonstrates a real user problem, thoughtful engineering, and a working product—not just an AI API call.

### Potential story angles

1. **Product thinking:** turning authentic German reading into a repeatable vocabulary-learning workflow.
2. **NLP engineering:** aligning German tokens and multi-word expressions with exact text offsets, including umlauts, `ß`, punctuation, and repeated occurrences.
3. **Reliable AI integration:** schema-validated contextual explanations with clear uncertainty and a separation between generated explanations and verified lexical facts.
4. **Backend design:** implementing a deterministic spaced-repetition scheduler with transactional review logging.
5. **Testing and reliability:** automated tests for ownership, scheduling, text offsets, and the complete reading-to-review journey.
6. **Data and analytics:** designing meaningful learning metrics without overstating what self-reported review ratings measure.

### Suggested LinkedIn narrative

When the project is working, describe:
- The learner problem and why you chose it.
- The core workflow and a short demo.
- One concrete engineering challenge and how you handled it.
- The tests or evaluation used to validate it.
- What you learned and what you would build next.

Avoid claiming that the app accurately certifies CEFR levels or measures real-world language mastery unless you have evidence to support those claims.

## 16. Practical build order

For the first implementation pass, work in this order:

1. Write `README.md` and `docs/architecture.md`.
2. Scaffold frontend, backend, database, and CI.
3. Create migrations and the first article endpoints.
4. Build the reading workspace and establish reliable text offsets.
5. Integrate spaCy for German text analysis.
6. Add the contextual-explanation provider interface and validated response schema.
7. Add vocabulary persistence and source context.
8. Implement the scheduler and append-only review logs.
9. Build the flashcard UI.
10. Add dashboard metrics.
11. Test the full workflow.
12. Deploy and polish the README, screenshots, and demo.

**Guiding principle:** Build a small, reliable product with a complete user journey. Make uncertainty visible, test the tricky parts, and document engineering decisions so the project is easy for another developer or recruiter to understand.
