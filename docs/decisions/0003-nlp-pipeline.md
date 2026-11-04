# 0003. German NLP pipeline: model choice, offsets, separable verbs, versioning

**Status:** Accepted

## Context

The reading workspace needs real linguistic data per article — tokens, lemmas, part-of-speech
tags, morphology, sentence boundaries, and separable-verb detection — to let a learner click a
word and see something useful. This step also had to backfill real article persistence (CRUD,
NFC normalization, a seed script, the Reader actually fetching an article by id): the task
assumed that layer already existed, and it didn't — confirmed by direct inspection before any
of the NLP work started.

## Model: `de_core_news_md`, pinned as a direct-URL dependency

spaCy ships three German pipelines. `sm` has no pretrained word vectors feeding its
tagger/parser/lemmatizer during training, so its tagging and dependency-parsing accuracy is
measurably behind `md`/`lg`. `md` and `lg` share essentially the same tagging/parsing/lemma
accuracy — the difference between them is almost entirely the size of the static word-vector
table (`lg`'s is ~25x larger), which this feature never touches (no `.similarity()` calls, no
vector-based features). `lg` would only add ~450MB to the CI cache and clone size for zero
benefit here, so `md` is the right trade-off: a real accuracy improvement over `sm` at a
fraction of `lg`'s size.

The model is pinned as a direct-URL wheel dependency (the officially documented way to install
a spaCy model reproducibly), not via a separate `spacy download` step:
```toml
dependencies = [..., "spacy>=3.8,<3.9", "de-core-news-md"]
[tool.uv.sources]
de-core-news-md = { url = "https://github.com/explosion/spacy-models/releases/download/de_core_news_md-3.8.0/de_core_news_md-3.8.0-py3-none-any.whl" }
```
This means `uv lock`/`uv sync --locked` installs it exactly like any other dependency — it's
hashed and pinned in `uv.lock`, and CI's existing `setup-uv` cache (already keyed on
`backend/uv.lock`) covers it automatically. No new CI step, no extra download logic to
maintain. The only consequence is a one-time ~40MB cache-miss download the first time this
lands; every run after that is cached.

The model is loaded once per process (`app/services/nlp/pipeline.py`'s `get_nlp()`, a
module-level singleton), not once per request — `spacy.load()` itself takes a few seconds, so
doing it per-request would make every single analysis unusably slow for no reason.

## spaCy stays behind our own types

`app/services/nlp/types.py` defines `Token`/`Sentence`/`SeparableVerb`/`AnalysisResult` as
plain Pydantic models; nothing outside `app/services/nlp/` ever imports `spacy` or touches a
`spacy.Language`/`Doc`/`Token` object. This is the usual dependency-inversion reason — the API
layer, the persistence layer, and the frontend all depend on our contract, not on spaCy's
object model, so the model or library could be swapped later without touching anything above
`app/services/nlp/analyze.py`.

## Offsets are Unicode code points; the UTF-16 conversion happens once, on the frontend

Python `str` indices already are Unicode code points — spaCy's `token.idx` needs zero
conversion to become our `start`/`end`. The alternative — also returning UTF-16 offsets from
the backend — was rejected because it doubles the offset payload for a value the frontend can
derive itself, and because duplicated offsets can drift out of sync if one is ever updated
without the other.

JavaScript string indices (and `String.prototype.slice`) are UTF-16 *code units*, not code
points. For any text containing a character outside the Basic Multilingual Plane (most emoji
are the practical case), a code point and its UTF-16 index diverge from that character
onward — every token after it would slice at the wrong position if the raw backend offset were
passed straight into `.slice()`. `frontend/src/lib/textOffsets.ts`'s `CodePointIndex` builds a
code-point → UTF-16-unit index once per article (`Array.from(text)`, which iterates by code
point — never `.split('')`, which iterates by UTF-16 unit and would tear a surrogate pair in
half) and every consumer slices through it. The rule is absolute: nothing in the frontend may
call `.slice()`/`.substring()` on `original_text` with a raw backend offset. A dedicated test
puts an emoji *before* a real word token specifically to catch a regression here.

**Invariant, tested on both sides:** `original_text[start:end] == token.text` in Python, and
the equivalent through `CodePointIndex` in TypeScript — checked against umlauts, `ß`, curly
quotes, em dashes, linebreaks, repeated words, NFC-decomposed input (normalized before
analysis, per below), and an emoji.

## Text is NFC-normalized once, at article creation

`app/services/article_service.py`'s `create_article` runs `unicodedata.normalize("NFC", ...)`
before storing — the only call site; the seed script and the API endpoint both go through it.
Offsets are defined against *that* stored string. Decomposed input (e.g. "ü" as `u` +
combining diaeresis) would otherwise shift every subsequent offset relative to what a learner
sees rendered, since a composed and decomposed form of the same visible character are a
different number of code points.

## Separable verbs: `dep_ == "svp"` and `tag_ == "PTKVZ"`, paired via `token.head`

Before writing any matching code, a verification spike ran the model against known
split-verb sentences and printed `dep_`/`tag_` for every token — confirming the signal
empirically rather than assuming it. `de_core_news_md` is trained on the TIGER/STTS German
scheme (not Universal Dependencies), where `svp` ("separable verb particle") is exactly this
relation and `PTKVZ` is its matching fine-grained tag. Requiring both — rather than either
alone — cuts false positives/negatives from either single statistical signal.

Combined lemma = `particle.lemma_.lower() + verb.lemma_.lower()` (particles don't inflect, so
`"an" + "rufen" = "anrufen"`, `"ab" + "fahren" = "abfahren"`). Represented as
`{lemma, verb_token_index, particle_token_index}` — indices into the flat token array, so the
frontend can highlight two non-contiguous spans together without the API duplicating token
data.

**Known limitations, found and confirmed empirically** (full detail and sentence examples in
`backend/tests/fixtures/nlp_known_failures.md`):
- An `anfangen` + `zu`-infinitive construction (`"Da fing sie an zu weinen."`) isn't detected:
  the particle gets `dep_="pm"` with the infinitive as its head, not `dep_="svp"` with the
  finite verb — a false negative by design, not a crash. The classic split/fronted pattern
  this feature targets is unaffected.
- A coordinated clause can cause a false-positive attachment: in the seeded article text
  `"Wir setzen uns auf eine Bank und essen zusammen."`, the parser attaches `zusammen` to
  `setzen` (forming the real verb `"zusammensetzen"`) instead of to the coordinated `essen`
  it actually modifies ("eat together"). Found during the manual walkthrough against real
  seed data, not a constructed test case — the detector has no way to disambiguate this from
  a genuine separable verb.
- A mistagged sentence-initial verb (e.g. a capitalized imperative, `"Mach dich auf..."`,
  tagged as a proper noun) can corrupt the computed combined lemma even though the particle
  attachment itself is found correctly — two independent failure modes that happen to show up
  in the same sentence.
- Predicative adjectives (`"Er ist sehr glücklich."`) are tagged `ADV`, not `ADJ`, per the
  TIGER scheme's own `ADJA`/`ADJD` distinction — not a separable-verb issue, but a quirk a
  learner could find confusing when inspecting the same word's part of speech.

## Morphology is labeled "detected," never "verified"

`token.morph.to_dict()` is passed through as-is — whatever keys the statistical morphologizer
produces (`Gender`, `Case`, `Number`, `Tense`, when present). It's a guess from a model, not a
dictionary fact, so the frontend panel renders it as "Detected: ..." text, consistent with
`docs/blueprint.md` section 8's rule never to present AI/model output as verified dictionary
data.

## Analyses are computed once per version, stored, and reused

`article_analyses` (`article_id`, `analysis_version`, `results` JSONB, `difficulty_estimate`,
`difficulty_details`, `created_at`, unique on `(article_id, analysis_version)`) exists so
re-opening the same article doesn't re-run spaCy every time, and so changing the pipeline later
doesn't silently rewrite history. `CURRENT_ANALYSIS_VERSION` is a plain code constant, bumped
by hand when the pipeline logic or model changes; a bump means the next request for that
article computes and stores a *new* row under the new version rather than overwriting the old
one. `get_or_create_analysis` (`app/services/analysis_service.py`) looks up
`(article_id, CURRENT_ANALYSIS_VERSION)`; on a miss it computes off-database (the spaCy call is
CPU-bound and shouldn't happen inside an open transaction) and inserts, catching `IntegrityError`
to re-fetch if a concurrent request won the race — the same pattern
`auth_service.register_user` already uses for the username/email race (see
[0002](0002-email-verification.md)).

One Pydantic schema, `app/schemas/analysis.py`'s `ArticleAnalysisResult`, is the single
round-trip contract: NLP output → that schema → `.model_dump(mode="json")` into `results` on
write → re-validated through the same schema on read. The stored JSONB shape and the API
response shape can't drift apart because they're the same type.

`difficulty_estimate`/`difficulty_details` exist as columns (per `docs/blueprint.md` section 7)
but are always `null` — the difficulty heuristic is separate, future work and is never faked.

## Measured cost (informs the "analyzing…" loading state)

Measured locally against the real pipeline, model already loaded (warm):
- The longest seeded text (1,593 chars, 260 tokens): **~124ms** compute, **~49 KiB** JSON.
- A synthetic text at the 50,000-character maximum (10,447 tokens): **~3.0s** compute,
  **~2.1 MB** JSON.
- Loading the model itself (once per process, not per request): **~3.7s**.

The JSON payload is larger than the raw text mainly because every token repeats its own field
names (`text`, `start`, `end`, ...) — JSON has no way to share keys across array elements.
Gzip over HTTP shrinks this substantially in practice (repeated key names compress very well),
and the field list matches what the task explicitly asked the contract to carry. The ~3 second
worst-case compute time is the concrete reason the Reader has a distinct "Analyzing text…"
state, separate from the (fast) initial article-loading state, and why analysis is fetched in
a second, sequential query rather than blocking the article view.

## Known limitations / next steps

- Difficulty estimation is designed for (columns exist) but not built — separate step.
- No dictionary validation of computed separable-verb lemmas; a parser mistake or an unusual
  sentence can still produce a non-real compound (see "known limitations" above).
- The eval fixture (`backend/tests/fixtures/nlp_eval.json`) is a small, manually reviewed set,
  not exhaustive coverage of German morphology — per `docs/blueprint.md` section 11, it's meant
  to catch regressions in cases already confirmed correct, not to prove general correctness.
