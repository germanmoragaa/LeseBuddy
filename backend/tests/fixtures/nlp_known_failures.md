# Known NLP pipeline limitations

Found and confirmed empirically against the real `de_core_news_md` model (not hypothetical).
Not asserted in `test_nlp_analyze.py` — documented here instead of hidden, per
docs/blueprint.md section 11 ("track known failure cases instead of treating every response
as correct").

## Predicative adjectives are tagged `ADV`, not `ADJ`

`"Er ist sehr glücklich."` → `glücklich` comes back as `pos=ADV` (fine-grained tag `ADJD`),
not `ADJ`. This follows the German TIGER/STTS annotation scheme's own distinction: `ADJA`
(attributive, inflected, pre-nominal — `"ein großes Haus"`) maps to the coarse tag `ADJ`,
while `ADJD` (predicative/adverbial use — `"das Haus ist groß"`) maps to `ADV`. It's correct
per the scheme, but a learner selecting `glücklich` in `"Er ist glücklich"` and seeing it
labeled "Adverb" instead of "Adjective" would reasonably find that confusing. Not something
our pipeline can fix without overriding the model's own tagging convention — flagged here
instead.

## `anfangen` + `zu`-infinitive isn't detected as a separable verb

`"Da fing sie an zu weinen."` — the particle `an` gets `dep_="pm"` (not `"svp"`) with
`"weinen"` (the infinitive) as its head, not `"fing"` (the finite verb our matcher expects).
Our detector requires `dep_ == "svp"`, so this construction produces no `SeparableVerb` entry
at all — a false negative by design, not a crash. The classic split/fronted pattern this
feature targets (`"Ich rufe dich morgen an."`, `"Der Zug fährt um acht ab."`) is unaffected.

## A coordinated clause can cause a false-positive separable-verb attachment

Found during the manual walkthrough against a real seeded article, not constructed as a test
case: `"Wir setzen uns auf eine Bank und essen zusammen."` ("We sit down on a bench and eat
together.") The parser attaches `zusammen` to `setzen` (`dep_="svp"`, `tag_="PTKVZ"`, head
`"setzen"`), producing the separable verb `"zusammensetzen"` ("to convene/get together") — a
real German verb, just the wrong reading here. The intended parse has `zusammen` as a plain
adverb modifying the *second*, coordinated verb `essen` ("eat together"), not `setzen`. Our
detector has no way to tell these apart; it trusts the parser's attachment. Coordinated
clauses sharing an implied subject/object across "und" are a plausible source of more cases
like this — not something this feature can fully rule out.

## A mistagged sentence-initial verb can corrupt the combined lemma

`"Mach dich auf, bevor es heiß wird."` — the particle attachment itself is found correctly
(`auf`: `dep_="svp"`, `tag_="PTKVZ"`, head `"Mach"`), but the parser tags capitalized,
sentence-initial `"Mach"` as a proper noun (`pos=PROPN`, `tag=NE`) instead of the imperative
verb `machen`. Its `lemma_` stays `"Mach"` rather than normalizing to `"mach"`/`"machen"`, so
the computed combined lemma (`particle.lemma_.lower() + verb.lemma_.lower()`) comes out as
`"aufmach"`, not the correct infinitive `"aufmachen"`. The particle-attachment detection and
the lemma-quality problem are two independent failure modes that happen to show up in the
same sentence here.
