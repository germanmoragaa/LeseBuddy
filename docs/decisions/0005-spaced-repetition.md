# 0005. Spaced repetition: a deterministic SM-2 variant, append-only logs, idempotent reviews

**Status:** Accepted

## Context

Backlog issue 10 (`docs/blueprint.md` sections 3D/7/12) needs a scheduler, a due-cards endpoint,
and a review log — the backend half of flashcard review. The flashcard UI itself is the next,
separate step; this change is backend-only.

## SM-2 variant, not FSRS

FSRS (the modern, ML-fitted scheduler several spaced-repetition tools have adopted) needs a
training corpus of real review outcomes to fit its parameters — this app has none yet, and a
portfolio project's first scheduler should be easy to explain and verify by hand. The classic
SM-2 algorithm, adapted from its original 0–5 grade scale to the four buttons every modern SRS
tool actually ships (Again/Hard/Good/Easy), is transparent: every interval is a short, named
formula in `app/services/scheduler.py`, not a fitted model. Revisiting FSRS once real review
history exists is a reasonable future step, not a correction of a mistake made here.

## Pure functions, no randomness

`schedule(state, rating, now) -> new_state` and `preview(state, now) -> {rating: interval_days}`
take every input explicitly (including "now") and do no I/O, no clock reads, and no
fuzz/jitter — the same inputs always produce the same output. This is what makes
`tests/test_scheduler.py`'s table-driven tests possible at all (an SM-2 with randomized fuzz,
the way some implementations add it to avoid review-pile clumping, couldn't be asserted against
exact expected values) and keeps all persistence and "what time is it" concerns in
`review_service.py`, where they can be mocked.

## Guaranteeing hard <= good <= easy, not just hoping the formulas produce it

The three formulas (`interval*1.2`, `interval*ease`, `good_interval*1.3`) naturally keep this
ordering whenever `ease_factor >= 1.2`, which the 1.3 floor guarantees — except for one
unusual-but-reachable case: a lone "easy" at `repetitions == 0` sets `interval_days = 4`, so the
*next* review enters `repetitions == 1`, where "good" is fixed at a flat 3 days regardless of
the actual stored interval — producing a raw `hard` (5) briefly larger than the fixed `good` (3).
Rather than leave this as an accepted rough edge, `_clamped_intervals` sequentially clamps
`good = max(good, hard)` then `easy = max(easy, good)`, so the invariant holds unconditionally,
not just for the common "same rating repeated" progressions. `preview()` and `schedule()` share
this one clamping function so the four rating buttons' displayed intervals can never disagree
with what pressing one of them actually applies.

## Card creation lives in `vocabulary_service`, not a separate step

A `Flashcard` is created in the same transaction as its `VocabularyItem`, due immediately — see
`vocabulary_service._get_or_create_item`. There's no "add this word to my flashcards" as a
distinct action the blueprint's screens describe or a separate on/off state to track: every
saved word is reviewable from the moment it's saved. The unique FK on
`flashcards.vocabulary_item_id` enforces "exactly one card per item" at the database level,
matching the blueprint's data-integrity rule against accidental duplicate cards. Deleting a
vocabulary item cascades its card (`ondelete="CASCADE"`); deleting an *article* never touches
either, matching the existing vocabulary-survives-article-deletion policy
([0004](0004-translations-and-dictionary.md)).

## Append-only review_logs, with a SET NULL instead of CASCADE

`review_logs` is never updated or deleted by application code — each row is reviewed-at-the-time
history, not current state (current state lives on `flashcards`). `flashcard_id` is
`ondelete="SET NULL"`, deliberately not `CASCADE`: a deleted vocabulary item's review history
should survive for future analytics (backlog issue 12) even though its card is gone. `lemma` is
snapshotted onto the log row for the same reason — once `flashcard_id` goes `NULL`, there would
be no other way to say what word a historical review was ever about.

## Idempotent submission, locked at the row level

`POST /api/v1/reviews` accepts an optional `client_review_id`. A retried or double-submitted
request with the same id returns the original log instead of re-applying the scheduler a second
time — checked both before locking (the common case: a second request simply finds the existing
log) and via `review_logs.client_review_id`'s unique constraint + `except IntegrityError` +
re-select on a genuine race (two concurrent requests with the same id), mirroring the
select → insert → rollback → re-select pattern already used by
`auth_service.register_user`/`analysis_service.get_or_create_analysis`/
`vocabulary_service._get_or_create_item`. The flashcard row itself is locked with
`SELECT ... FOR UPDATE` for the duration of the transaction, so a second request (same or
different `client_review_id`) can't interleave its own read-modify-write of the card's scheduling
state with the first's — both the card update and the log insert commit together or roll back
together.

## Clock injected, not read from `datetime.now()` inline

`GET /due`, `GET /summary`, and `POST /reviews` all take a `now_fn` dependency
(`app/api/deps.py:get_clock`, a zero-arg callable returning `datetime.now(UTC)` by default) so
tests can override it with a fixed instant instead of needing to freeze real time or tolerate
timing-dependent assertions — the same reasoning that makes `TranslationProvider` and
`EmailSender` injectable rather than imported directly. New-card creation in
`vocabulary_service` still calls `datetime.now(UTC)` directly: it isn't part of the reviewable
flow this ADR covers, and a freshly-saved word being due "now" in real wall-clock time is the
correct behavior regardless of what a test later pretends "now" is for reviewing it.

## Known limitations

- No FSRS/ML-fitted scheduling yet — see above; revisit once real review history accumulates.
- The migration backfills every pre-existing `vocabulary_item` with a due-now card in a single
  `INSERT ... SELECT`, bypassing `vocabulary_service`'s one-card-per-item invariant check — safe
  only because the unique FK means this can't double-insert, and only because this runs once,
  before the API exists for anyone to have reviewed anything yet.
- `review_logs` has no `interval_days_after`/"before" column distinct from
  `previous_interval_days`/`new_interval_days` as named in `docs/blueprint.md` section 7's
  suggested schema — the same data, named to match this implementation's own
  previous/new-prefixed convention instead of the doc's literal column names.
