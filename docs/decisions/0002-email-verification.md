# 0002. Email verification: one-time code, hashed and rate-limited

**Status:** Accepted

## Context

Registration and login exist ([0001](0001-authentication.md)), and `users.email_verified_at`
was already designed for but unused. This step confirms that a registered email address is
real and reachable, without blocking login itself: unverified users can log in, but every
`/app` route and app API endpoint is gated behind verification.

## A 6-digit code, not a confirmation link

Both are standard. A code was chosen because:
- It works without the frontend parsing a token out of a URL — the user types six digits into
  the same tab they're already on, which also means it survives the link being opened in a
  different browser/device than the one mid-signup (a common failure mode for confirmation
  links, since some mail clients also prefetch/scan links, silently "clicking" them).
- It composes trivially with a session-based "resend" flow: the user is already logged in
  (just unverified), so resending/verifying are just two more authenticated endpoints, not a
  separate unauthenticated token-lookup path.

The trade-off is a worse experience on devices where typing is painful, and a non-zero guess
space — both addressed below.

## Codes are stored HMAC-hashed, not plaintext or a plain hash

`hash_verification_code` is `hmac.new(SECRET_KEY, code, sha256)`, compared with
`hmac.compare_digest` (constant-time, so comparison timing can't leak how many leading digits
matched). A 6-digit code has only 1,000,000 possible values — an unsalted/unkeyed hash (plain
`sha256(code)`) would let anyone who reads the `email_verification_codes` table (backup, SQL
injection, misconfigured replica) brute-force every stored code in well under a second, since
there's no per-row salt to force recomputation and the keyspace is tiny either way. Keying the
hash with a server-side secret means a stolen table alone isn't enough — `SECRET_KEY` is also
needed, and that secret never lives in the database. This is also why the attempt limit below
matters even though the hash is strong: the real defense against *online* guessing is the
5-attempt cap, not the hash.

`SECRET_KEY` is new in this step (0001 deliberately avoided needing one). It has an
obviously-fake default (`dev-only-insecure-secret-change-in-production`) for local dev and CI,
and **must** be overridden with a long random value in any real deployment — documented loudly
in `.env.example`.

## Expiry (15 min) and a 5-attempt cap, enforced server-side

Both limit how long a leaked/intercepted code stays useful and how many guesses an attacker
gets against the real code, independent of the hashing. `attempts` lives on the code row itself
and increments on every wrong guess; once it hits 5, that code is dead even if the correct value
is guessed afterwards — the user must request a new one. Expired/exhausted codes get distinct,
actionable error messages ("request a new code") rather than a generic failure, since the
recovery path differs from a simple typo.

## Resend is rate-limited at the database, not an external store

A 60-second cooldown between requests plus a 5-per-hour cap, both enforced by querying
`created_at` timestamps on the user's own `email_verification_codes` rows — no Redis or
in-memory counter needed at this scale, and the limits survive a backend restart for free since
they're just rows. Issuing a new code marks every still-active code for that user `consumed_at
= now()` (not deleted): deleting would lose the issuance history the hourly cap depends on.

## Unverified users can log in, but can't use the app

Blocking login entirely until verification would mean a user who mistyped their email, or whose
provider delayed the mail, can't even get back in to see their own account or retry. Instead:
`get_current_user` (any logged-in user) stays the gate for auth endpoints, `/me`, logout, and
the verification endpoints themselves — all of these have to work *for* unverified users, or
there's no way to verify or recover. A new `get_current_verified_user` additionally requires
`email_verified_at IS NOT NULL`, returning 403 with a machine-readable
`{"code": "email_not_verified"}` body, and gates every real app endpoint (today: the
`/api/v1/articles` placeholder). The frontend mirrors this at the route level: `ProtectedRoute`
redirects a logged-in-but-unverified user to `/verify-email` instead of rendering `/app/*`.

## Uniqueness is enforced at the database, not just in application code

0001's `email` column was `unique=True` — a real constraint, but only *effectively*
case-insensitive because every write path happened to lowercase first. This step replaces it
with a functional unique index on `lower(email)` (mirroring the existing username index), so
`alice@x.com` and `ALICE@x.com` can never both exist even if a future code path forgets to
normalize. No backfill was needed: every stored email was already lowercase.

**The race this closes:** two requests registering the same username/email simultaneously can
both pass the pre-check (neither has committed yet) and both attempt to insert. The database's
unique index is the actual source of truth — it lets exactly one `INSERT` through and raises
`IntegrityError` for the other. `register_user` catches that, re-queries to find out *which*
column actually conflicted now that the real row is committed, and raises the matching
`UsernameTakenError`/`EmailTakenError` — mapped by the API to the same field-specific 409 the
pre-check path already returns. The caller can never tell whether they hit the fast pre-check
path or the race-recovery path; neither can ever surface a 500.

## Unverified accounts expire after 24 hours and free their slot

Without this, someone who registers with a typo'd email (or never receives the mail) would
permanently squat on that username/email, since nothing else ever deletes an unverified
account. Instead, `register_user` first checks whether the requested username *or* email belongs
to an unverified account older than `UNVERIFIED_ACCOUNT_TTL_HOURS` (24h) and, if so, deletes it
in the same transaction before proceeding — `sessions.user_id` and
`email_verification_codes.user_id` both cascade on delete, so its sessions and codes go with it
automatically. Doing the delete and the new insert in one transaction (flush, not commit, for
the delete) means Postgres's read-your-own-writes guarantees the uniqueness check that follows
sees the slot as already free — there's no window where a concurrent request could see the slot
freed but fail to claim it, and no separate background job/scheduler is needed at all.

A *verified* account is never touched by this, regardless of age — expiry only ever reclaims
abandoned, never-verified signups.

## Email is sent only after the user is committed, and never blocks the response

`register_user` commits the new user row before anything emails-related happens; the
registration endpoint then calls `issue_verification_code` (also committed) and hands the send
itself to `BackgroundTasks`, so the HTTP response returns immediately after the user exists and
is logged in — sending mail (DNS, SMTP handshake, provider latency) never adds to that latency.
The background task's own `try/except` swallows any send failure and just logs it: a transient
SMTP outage must never make registration itself fail, because the user's recovery path (hit
"resend") only exists once they're registered and logged in. The trade-off is that a user can
occasionally register and *not* get a first email — expected, and why resend exists.

## Email delivery: a small interface, swapped per environment

`app/services/email.py` defines an `EmailSender` protocol with two implementations:
`SmtpEmailSender` (stdlib `smtplib`, points at [Mailpit](https://github.com/axllent/mailpit)
locally — a fake SMTP server with a web UI at `localhost:8025`, added to `docker-compose.yml`)
and `FakeEmailSender` (in-memory `.sent` list). Tests inject the fake via a FastAPI dependency
override and never touch a socket; CI never needs Mailpit or any real mail provider. No new
dependency was needed — `smtplib` and `email.message` are both stdlib.

## Known limitations / next steps

- **No email-change flow.** A verified user has no way to update their email address yet;
  that would need its own re-verification step.
- **No password reset.** Noted as a `SECRET_KEY`-shaped gap in 0001; this step introduces that
  secret, so a reset-token flow is now unblocked but still not built.
- **Client-side resend countdown is approximate.** The UI seeds its countdown from a constant
  matching the server default and from the server's `retry_after` after a 429, but doesn't
  persist across a page reload — reloading mid-cooldown shows "Resend code" enabled again, and
  the very next click will correctly get a 429 with the real remaining time. Cosmetic only; the
  server-side cooldown is the actual enforcement.
- **No account deletion/email-change cleanup for verified accounts.** The 24-hour expiry only
  ever reclaims unverified signups, by design — there's no equivalent cleanup path for verified
  accounts, which don't need one yet.
