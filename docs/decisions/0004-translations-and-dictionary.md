# 0004. Contextual translation and dictionary data: DeepL + Wiktionary, not an LLM

**Status:** Accepted

## Context

The reader already shows spaCy's statistically *detected* lemma/POS/morphology
([0003](0003-nlp-pipeline.md)), but has no actual meaning, translation, or grounded grammatical
facts (gender, plural, glosses), and "Save to vocabulary" was a disabled stub. This step makes
the word-detail panel genuinely useful and turns saving into a real, deduplicated personal
vocabulary — backlog issues 8 and 9 (`docs/blueprint.md` sections 3B/3C/7/8/10/11).

## Why DeepL + Wiktionary instead of an LLM

`docs/blueprint.md` section 8 calls for grounding dictionary facts in a reliable lexical source,
not model-generated guesses — an LLM asked "what gender is this noun?" is still a statistical
guess dressed as prose, with no mechanism to be *wrong in a detectable way*. Three concrete
reasons drove this:

- **Cost.** A paid LLM API call per word lookup doesn't fit a portfolio project's budget; DeepL's
  Free plan (500,000 characters/month) and Wiktionary's openly-licensed data are both free.
- **Verifiability.** A dictionary entry's gender/plural either matches Wiktionary's data or it
  doesn't — there's no hallucination risk for facts that come from a lexical database. Grammar
  facts and translations come from two different, independently-checkable sources instead of
  one black box.
- **Determinism.** The same word in the same sentence translates to the same cached string every
  time (see caching below), which an LLM's non-deterministic sampling doesn't give for free.

The trade-off, accepted and documented below: no natural-language grammar *explanations* ("this
is accusative because..."), and idiom coverage depends entirely on whatever Wiktionary happens
to have a phrase entry for.

## Provider interface, so an LLM explainer could sit behind the same seam later

`app/services/translation/provider.py` defines a `TranslationProvider` Protocol
(`translate(text, *, context, target_lang) -> str`, `get_usage() -> UsageSnapshot`), mirroring
the existing `EmailSender` protocol shape ([0002](0002-email-verification.md)).
`DeepLTranslationProvider` wraps the official `deepl` SDK's `DeepLClient` (not the deprecated
`Translator`), which auto-detects Free-vs-Pro from the key's `:fx` suffix. `FakeTranslationProvider`
is a deterministic, test-only implementation injected via a FastAPI dependency override — tests
and CI never call the real API. `NullTranslationProvider` is returned by
`app/api/deps.py`'s `get_translation_provider()` when `DEEPL_API_KEY` is empty: the app still
starts, and any translation attempt raises the same typed `TranslationNotConfiguredError` a bad
real key would raise, which the API maps to a 503 with a clear `{"code": "translation_not_configured"}`
body the UI shows gracefully instead of retrying forever.

DeepL's `context` parameter — free, uncounted toward billing, available on the Free plan — lets
the containing sentence disambiguate a single word's translation without the sentence itself
being translated or billed. German source is hardcoded (`SOURCE_LANGUAGE = "DE"` in
`deepl_provider.py`) — there's no source-language setting; this app only ever translates *from*
German, and adding other source languages is out of scope, not an oversight.

## Two separate endpoints, not one combined one

`GET /api/v1/articles/{id}/dictionary` (free, local, instant — safe to fire automatically on
every word click) and `POST /api/v1/articles/{id}/translate` (quota-limited) are independent,
mirroring the existing precedent of `/analysis` being its own endpoint rather than folded into
`GET /articles/{id}`. spaCy data needs no endpoint of its own — the frontend already has it from
`/analysis`. `WordDetailPanel.tsx` fires both the dictionary and the word-translation query in
parallel on every click (each with its own independent loading/error state), plus a manual
"Translate sentence" button (`include_sentence=true` on the same `/translate` call) kept
separate because sentence translation is explicitly "on request, to save characters." If a
translate call ever comes back not-configured or quota-exceeded, the frontend stops auto-firing
word translation for the rest of that session (`Reader.tsx`'s `translationDisabled` state, lifted
above the panel so it survives the panel remounting on every new selection) and shows a static
message instead of silently retrying — and re-logging — on every subsequent click.

## Server-side context building, never client-sent context

`app/services/selection.py`'s `resolve_selection(analysis, original_text, start, end)` — one
implementation, shared by `/translate`, `/dictionary`, and the vocabulary save endpoint — takes
only `{start, end}` and does two things a client-sent context string could never be trusted to
do honestly:

1. **Boundary validation.** Both offsets must exactly match real token boundaries from the
   article's own stored analysis — never an arbitrary mid-token slice, which would let a client
   pick any substring to translate (and bill) regardless of what's actually on screen.
2. **Sentence lookup.** The containing sentence is found from the stored `sentences[]`; if no
   single stored sentence fully contains the selection, the request is rejected with 422 rather
   than guessing a merged context. The sentence text *is* the DeepL `context` value — derived
   from the article's own stored text, never accepted as a request field at all.

A token that's part of a separable verb resolves to its combined lemma (e.g. "anrufen") for
dictionary lookup; a contiguous multi-token selection resolves to the sliced phrase text for
phrase lookup/translation.

## Translation cache: one combined hash, not a two-column key

`translation_cache` is keyed by a single indexed column,
`cache_key = sha256(source_text + "\0" + context + "\0" + target_lang + "\0" + provider)`
(hex digest, fixed length) — `source_text`/`context`/`target_lang`/`provider` are still stored as
plain columns for debuggability, just not part of the index. Hashing only `context` was
considered and rejected: a whole-sentence translation (the "Translate sentence" action) has no
context at all, just a long `source_text` — the same "long text in a unique index" problem the
hash was meant to solve in the first place. **Deliberately excludes the user ID**: the same
German word in the same sentence translates to the same string regardless of who's asking, so
two different users both looking up "Herausforderung" in the same sentence share one cache row
and only the first ever actually calls DeepL. `provider` is a plain string (`"deepl"`) so a
second provider later needs no schema change. No `source_lang` column, matching the hardcoded
German-only source above.

`lookup_cached_translation()` is cache-only — it never calls the provider, is never rate-limited,
and is never logged — used by vocabulary save, so saving a word the user already saw translated
in the panel can never trigger a second, newly-billed DeepL call.

## Rate limiting: a request-log table, not a bare count

`translation_request_log(user_id, created_at)` gets one row per **successful, non-cached** DeepL
call only (gated by inserting it from inside `_translate_cached`, right after the real provider
call succeeds — a cache hit returns before that code ever runs). `_check_rate_limit` queries rows
in the last hour and, once at `TRANSLATION_RATE_LIMIT_PER_HOUR` (default 60), computes a real
`Retry-After` from the *oldest* row in that window — mirroring
`auth_service.issue_verification_code`'s hourly-cap shape ([0002](0002-email-verification.md))
rather than a bare `count() >= limit` that can't say when the limit will lift. A low-stakes race
(two concurrent requests from the same user's session could both pass the under-limit check
before either logs its row) is accepted and documented here rather than fixed with extra
locking — not worth it at this app's scale, and the consequence is at most one extra DeepL call
over the limit, not an unbounded one.

## Quota check: cached with a short TTL, and fails open

`provider.get_usage()` is a second DeepL round trip on top of the actual translation — calling it
on every single request adds latency and a second failure point for a check whose only purpose
is graceful degradation, not security. `DeepLTranslationProvider` caches the last usage snapshot
in-process, refreshing it only if older than `TRANSLATION_USAGE_CHECK_INTERVAL_SECONDS` (default
300s). If the usage check itself fails, a warning is logged and the real translation proceeds
anyway — a broken diagnostic call must never block an otherwise-working translation. When usage
crosses `TRANSLATION_USAGE_WARN_THRESHOLD` (default 90%), the response carries a `quota_warning`
string the UI surfaces next to the translation; at 100% of a known limit, new non-cached
translations raise `TranslationQuotaExceededError`, mapped to 429.

## Dictionary dataset: kaikki.org's English-Wiktionary German extract

kaikki.org publishes two candidates: the German-Wiktionary extraction (German-language glosses,
and would need self-filtering from a ~2.9GB full dump since it's not pre-filtered to any single
target language) and the English-Wiktionary German-filtered extract (`de-extract.jsonl.gz`,
~296MB gzip, already pre-filtered to German entries, with English glosses). The latter was
chosen: German-language glosses would be circular for a learner still building vocabulary, and
the English-Wiktionary extract needs no self-filtering step. Both datasets have comparable
gender/plural/inflected-form coverage for common vocabulary — the gloss language was the
deciding factor.

**No stable, dated download URL exists upstream** — kaikki.org overwrites the file in place on
each rebuild; there is no way to pin an exact version the way a package registry would allow.
`--source-version` (default: today's date, stamped on every imported `DictionaryEntry` row) is
the closest available approximation to a pinned version, not a real one — documented here as a
known, accepted limitation rather than an oversight.

`app/scripts/import_dictionary.py` streams the gzip JSONL line by line (never loading the whole
file into memory) and replaces the dictionary tables in **one transaction**: `TRUNCATE`, then
stream-insert with periodic `flush()`+`expunge_all()` (bounded memory without losing atomicity),
then a single final `commit()` after the entire file has been processed successfully. This means
concurrent lookups see the complete previous dataset for the whole duration of the import (not a
half-imported table), and a crash mid-import rolls back to the previous good dataset for free —
rejected alternative: committing in batches, which would let a crash leave the table
partially-replaced with no way to tell old rows from new ones. Every `pos` string kaikki
provides is kept verbatim, with no allowlist — idiom/phrase entries are tagged `pos == "phrase"`
and must survive import unfiltered for phrase lookups (e.g. "vor allem") to work at all. Gender
tags (`"masculine"/"feminine"/"neuter"`, kaikki's own string tags inside `senses[].tags`, not a
dedicated field) are normalized to spaCy's own morph codes (`Masc`/`Fem`/`Neut`) **at import
time** — so neither the lookup service nor the frontend ever needs a second gender vocabulary,
and `grammarLabels.ts`'s existing `MORPH_VALUE_LABELS` renders both sources through one code path.

CI never downloads the real dataset — `tests/fixtures/dictionary/sample.jsonl` is a small,
hand-written file in kaikki's real line format (a noun, a separable-verb entry, a phrase, and a
deliberate heteronym pair), and `test_dictionary_import.py` imports that fixture, never the live
URL.

## Dictionary lookup: lemma first, then surface-form fallback, never a guess

`dictionary_service.resolve_dictionary_entry` looks up by spaCy's detected lemma + POS first; on
a miss, falls back to `dictionary_forms` (an inflected-form → lemma index populated at import
time from kaikki's `forms[]`) keyed by the raw surface text, for inflections the lemmatizer
normalizes differently than Wiktionary spells its headword. Separable verbs look up by their
combined lemma (e.g. "anrufen", not "rufen"); multi-word selections look up the sliced phrase
text directly against phrase entries. **Returns `None` on no match, never a guessed or
closest-match entry** — the frontend renders "No dictionary entry found for this word" rather
than a fabricated fact, consistent with the "never present model output as verified dictionary
data" rule already established in [0003](0003-nlp-pipeline.md).

**Accepted limitation: heteronym collisions.** The dictionary has no disambiguation between two
different words that share a spelling but differ in gender/meaning (e.g. "der Kiefer" — jaw —
vs. "die Kiefer" — pine tree) — `dictionary_entries` has no uniqueness constraint, so both rows
exist, but lookup by lemma alone can only return one. Widening the lookup key to also include
part-of-speech was considered and rejected: both senses of "Kiefer" are nouns, so it wouldn't
actually resolve the stated example — it would just give false confidence that the problem was
fixed. Not solved in this step; noted as real, not papered over.

## Dictionary wins on gender disagreement — a frontend merge rule

spaCy's morphologizer and the dictionary arrive in two separate HTTP responses, by design (the
endpoint split above). `WordDetailPanel.tsx` composes a single resolved-gender line via
`grammarLabels.ts`'s `resolveGender(detectedGender, dictionaryGender)`: the dictionary's value
wins whenever it has one — it's a verified lexical fact, not a per-sentence statistical
guess — and the UI labels which source won ("Dictionary" vs. "Detected"), rather than ever
showing two contradicting gender lines side by side. `formatMorph`'s `excludeGender` option keeps
the rest of the detected morphology (number, case, tense) rendering through the existing single
code path, with gender excluded from that line since it's shown separately above.

## Vocabulary: a backend-computed snapshot, never a client-trusted payload

`POST /api/v1/vocabulary` accepts only `{article_id, start, end}` — matching every other
"never trust the client for anything derivable server-side" precedent already in this codebase
(NFC normalization, offset validation, ownership checks). `vocabulary_service.save_occurrence`
re-derives the lemma/POS/separable-verb status via `resolve_selection`, re-runs the dictionary
lookup, and reuses whatever's already in `translation_cache` for that exact
selection+context+language (never a fresh billed DeepL call at save time — the user already saw
the translation in the panel before clicking "Save"), then snapshots all of it into
`vocabulary_items`/`article_vocabulary`. Saved data is copied, not referenced — a saved item
never depends on `dictionary_entries` or `translation_cache` staying unchanged (e.g. a future
dictionary re-import must never retroactively change what a user already saved).

**Dedup key: `(user_id, lower(lemma_or_expression))`.** Saving the same lemma/expression twice
reuses the existing `vocabulary_items` row and only adds a new `article_vocabulary` occurrence
row if that exact `(article_id, start_offset, end_offset)` combination isn't already saved —
unique at the database level on both tables, with the same
select → compute off-DB → insert → `except IntegrityError` → rollback → re-select → assert race
pattern `auth_service.register_user` and `analysis_service.get_or_create_analysis` already use.
**Accepted limitation, same shape as the dictionary's:** a heteronym pair collapses to one saved
item under this key, for the same reason widening it wouldn't actually fix the stated example.

**Article deletion policy** (`docs/blueprint.md` section 7): `DELETE /api/v1/articles/{id}`
cascades to that article's `article_analyses` and `article_vocabulary` rows only (both have
`ondelete="CASCADE"` foreign keys to `articles`) — `vocabulary_items` have no FK to articles at
all, so a user's saved vocabulary survives deleting the article it came from; only the
per-article occurrence record (and therefore that word's highlight/context link back to the
now-gone article) disappears.

## Translation-language preference

`users.translation_language` (`String(8)`, server default `"EN-US"`) supports at least English
and Spanish (`SUPPORTED_TRANSLATION_LANGUAGES = {"EN-US", "ES"}` in `app/schemas/auth.py`,
enforced by a Pydantic validator so an unsupported code can never be stored) and is read by
`translate_selection` as the DeepL target — never sent per-request by the client, so a user can't
spoof a different target language than their own saved preference. Editable via
`PATCH /api/v1/me` (gated by plain `get_current_user`, not the verified-user dependency — a
logged-in-but-unverified user must still be able to change this). The frontend exposes it on its
own `/app/settings` page (reachable from the sidebar's account menu) rather than an inline
control in that menu's dropdown, since the dropdown is sized for single-action buttons like "Log
out" and there's no `<select>`-style component in the design system yet.

## License and attribution

Wiktionary's content (and kaikki.org's machine-readable extraction of it) is licensed
[CC BY-SA](https://creativecommons.org/licenses/by-sa/3.0/) — share-alike attribution is a real
license requirement, not a courtesy. Every place dictionary data renders in the UI
(`WordDetailPanel.tsx`) shows a visible "Dictionary data from Wiktionary, licensed CC BY-SA" line
next to it; the README documents the same attribution for anyone redistributing this project.
Machine-translated text (DeepL) carries no equivalent redistribution requirement and needs no UI
attribution beyond being clearly labeled "machine translation" (source-labeled per the next
section).

## Every field is labeled with its source

The panel combines three independent sources (spaCy "Detected", the dictionary, and machine
translation) that can legitimately disagree — presenting them unlabeled would imply one single
authoritative answer where there are really three different kinds of claim with different
reliability. `DictionaryEntryRead.source_label` (deliberately not named `source` — that name
collides with the ORM model's own `source` column, which holds dataset provenance like
`"kaikki-de-extract"`, and `from_attributes=True` validation would silently prefer the ORM value
over the schema's intended default; found and fixed during implementation, now a commented
warning in the schema) and `TranslateResponse.source` (`"machine_translation"`) both exist purely
so the frontend never has to guess which bucket a field belongs in.

## Known limitations

- No natural-language grammar explanations — a dictionary entry gives facts (gender, plural,
  glosses), not prose reasoning about *why* a form is used, which was an explicit trade-off for
  avoiding LLM non-determinism and cost.
- Idiom/expression coverage is exactly whatever Wiktionary happens to have a phrase entry
  for — many valid German expressions simply return no dictionary entry.
- Heteronym collisions (dictionary lookup and vocabulary dedup both) are real, documented, and
  not solved — see above.
- No pinned dictionary dataset version — only a best-effort date stamp, since kaikki.org exposes
  no stable versioned download.
- DeepL's Free-plan 500,000 characters/month is shared across every user of this deployment; the
  per-user hourly rate limit protects against one user's burst usage but doesn't partition the
  monthly quota per user.
