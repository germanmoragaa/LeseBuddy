# 0006. Songs and lyrics: Genius for metadata only, lyrics pasted by the user and kept private

**Status:** Accepted

## Context

LeseBuddy is changing direction: instead of a general "paste a German article" reader, it
becomes an app for learning German from song lyrics. A user looks up a song, saves it with its
metadata, pastes the lyrics, and reads them with the existing Reader, saving the words they learn
to their vocabulary. Pasting your own non-song text stays available as a secondary option.

Nearly everything built so far keeps working unchanged: a song is stored as an `articles` row
with `kind = "song"` plus a 1:1 `songs` metadata row, so the spaCy analysis, offsets, Reader,
DeepL/Wiktionary lookups, vocabulary, decks, and SRS all keep operating on articles. The open
question this ADR settles is **where the song data comes from**, and specifically where the
lyrics come from, since lyrics are copyrighted and the obvious technical shortcuts are not
legally or practically usable.

The rollout is phased (see the "Direction change (songs)" section at the top of
[`docs/blueprint.md`](../blueprint.md)); this ADR is phase 0 and adds no feature code.

## Decision

- **Genius official API, for search and metadata only.** Song search and per-song metadata
  (title, primary artist, album, release date, cover image URL, Genius page URL) come from the
  official Genius API, authenticated with a client access token (`GENIUS_ACCESS_TOKEN`). The
  official API does not return lyrics, and the app never tries to get them another way.
- **No lyrics scraping, ever.** No code fetches lyrics from Genius' web pages or any other
  third-party site. The `lyricsgenius` library (which scrapes lyrics from Genius' HTML) is not
  used.
- **Lyrics are pasted by the user and private to that user.** The user supplies the lyrics
  text themselves. A saved song, including its lyrics, is visible only to the user who saved
  it — no sharing, no public libraries, no community-contributed lyrics.
- **Covers are hotlinked, not copied.** Cover art is displayed from the URL the Genius API
  returns; images are never downloaded to or re-served from our server.
- **Attribution.** Every song with Genius metadata links to its Genius page.
- **Songs not on Genius** can still be saved with a manually entered title and artist (the
  Genius id is optional).
- **Provider interface.** Genius sits behind a provider interface, the same way DeepL sits
  behind `TranslationProvider` ([0004](0004-translations-and-dictionary.md)): a real Genius
  provider in dev/prod, a fake provider in tests, and graceful "not configured" behavior when
  `GENIUS_ACCESS_TOKEN` is empty (the app must start without it). Tests and CI never call
  Genius.
- **The backend never trusts client-sent metadata.** When a song is saved by Genius id, the
  backend re-fetches its metadata from the provider by that id, mirroring how vocabulary save
  accepts only `{article_id, start, end}` and re-derives everything else.

## Alternatives considered

### Scraping lyrics with LyricsGenius (rejected)

The convenient path — search Genius, then let `lyricsgenius` pull the lyrics — is rejected:

- It works by scraping Genius' web pages, which the library's own documentation acknowledges is
  against Genius' terms of service.
- Genius actively blocks these requests from server and cloud IP ranges (HTTP 403), so it would
  fail in deployment and in CI even setting the legal problem aside.
- Lyrics are copyrighted works, and German copyright law has no general fair-use exception that
  would cover copying them into an app's database.

### Musixmatch API (rejected)

The free tier returns only a fragment (roughly 30%) of each song's lyrics; full lyrics require
a commercial licence. A partial song is useless for reading practice, and a commercial licence
is out of scope for a non-commercial portfolio project.

### Manual-only entry, no metadata provider (rejected)

Users would type title and artist and paste lyrics with no lookup. It avoids any third-party
dependency, but loses covers, canonical titles/artists, release dates, and the attribution
link — a noticeably worse experience for the app's central screen. It remains available as the
fallback for songs Genius doesn't have, not as the primary path.

## Consequences

- **User-facing terms of use** before public deployment: users only upload content they have
  the right to use, for personal study; a contact address for takedown requests, and content is
  removed when one arrives.
- **Impressum and a GDPR-compliant privacy policy** before public deployment (the app targets
  deployment in Germany).
- **Public-domain material only** for anything we publish ourselves: demo account, seed data,
  screenshots, README, videos. That means original texts of Volkslieder or Lieder whose lyricists
  died more than 70 years ago — never copyrighted lyrics.
- **No real copyrighted lyrics in the repo.** Fixtures, tests, seed data, and docs use invented
  lyric-style lines or public-domain texts.
- **Tests and CI never call Genius** — a fake provider is injected, as with DeepL.
- **Genius API terms** must be re-checked against the current version before deployment.
- Lyrics break some assumptions of the current NLP pipeline (apostrophe contractions such as
  `hab'`/`dei'm`, anglicisms, little punctuation, so line-based rather than sentence-based
  context). That is handled in a later phase with an evaluation set of invented lines, not here.

This is a general framework for keeping a non-commercial portfolio project on the right side of
copyright and platform terms, **not legal advice**. If LeseBuddy ever becomes a public or paid
product, these decisions should be reviewed with a lawyer.
