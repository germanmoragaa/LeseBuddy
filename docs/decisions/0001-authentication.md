# 0001. Authentication: passwords, sessions, cookies, CSRF, brute-force

**Status:** Accepted

## Context

LeseBuddy needs accounts: register, log in, log out. Everything a logged-in user does later
(saving articles, vocabulary, flashcard reviews) needs to be scoped to an owner, so this has to
land before any of that.

## Password hashing: Argon2id via pwdlib

`pwdlib[argon2]`, using `PasswordHash.recommended()` — this is what the current FastAPI docs
recommend. Argon2id is the OWASP/NIST-era consensus choice for password hashing: it's
memory-hard, which makes GPU/ASIC cracking far more expensive than bcrypt or PBKDF2, and the
"id" variant mixes the side-channel resistance of Argon2i with the GPU-cracking resistance of
Argon2d. Passwords are never logged or stored in plaintext anywhere, including in error paths.

## Password policy: NIST SP 800-63B, not composition rules

Minimum 8 characters, maximum 128, no forced uppercase/digit/symbol rules. This follows current
NIST guidance: forced composition rules push users toward predictable patterns (`Password1!`)
and don't meaningfully improve resistance to guessing, while a generous length limit (128, not
the old-school 16-20) lets people use long passphrases, which are what actually resist brute
force. A denylist against known-breached passwords (e.g. the HaveIBeenPwned k-anonymity API) is
a reasonable next step but is **not implemented in this step**.

## Server-side sessions, not JWTs

A session is a row in `sessions` (user_id, hashed token, `expires_at`, `last_used_at`), looked up
on every request. The alternative — a signed/stateless JWT in the cookie — would avoid a DB
lookup per request, but:
- **Revocation is immediate and real.** Logout (or a future "log out everywhere" / admin action)
  deletes the row; the session is dead right away. A JWT is valid until it expires no matter
  what you do server-side, unless you also maintain a revocation list — at which point you've
  rebuilt sessions anyway, with extra steps.
- **No signing secret to manage.** Nothing is signed or encrypted, so there's no `SECRET_KEY` to
  generate, rotate, or leak. If a later feature needs to sign something (e.g. a password-reset
  link), that's the moment to introduce one — not preemptively here.
- The DB lookup cost is a non-issue at this scale, and `last_used_at` (useful for "active
  sessions" UI later) falls out of the same row for free.

## Session tokens are stored hashed, not in plaintext

The raw token (`secrets.token_urlsafe(32)`) is the actual bearer credential — anyone who has it
is logged in as that user. Only `sha256(token)` is stored. A leaked `sessions` table (backup,
SQL injection, misconfigured replica) is then useless without the original high-entropy random
value, the same reason API keys and OAuth tokens are never stored in plaintext.

## Cookie settings

`HttpOnly` (JavaScript, including any future XSS payload, can't read it), `SameSite=Lax`
(sent on top-level navigation but not on cross-site POST/PUT/DELETE — see CSRF below), `Path=/`,
`Secure` driven by `SESSION_COOKIE_SECURE` (false for local http, must be true wherever the app
is served over https). 30-day expiry (`SESSION_DURATION_DAYS`).

## CSRF: SameSite=Lax + JSON-only bodies is enough for now

Two independent layers:
1. **`SameSite=Lax`** is the real defense: modern browsers don't attach the cookie to a
   cross-site POST/PUT/DELETE at all (only to top-level GET navigation), so a malicious site
   can't ride the user's session to call a state-changing endpoint.
2. **State-changing endpoints only accept `application/json` bodies.** A plain HTML form can
   only submit `application/x-www-form-urlencoded`, `multipart/form-data`, or `text/plain` — it
   cannot set `Content-Type: application/json` without JavaScript, and cross-origin JS can't get
   that request to carry credentials without also triggering CORS, which the backend doesn't
   grant. This is defense-in-depth for the small set of legacy clients that might not honor
   `SameSite`, not the primary mechanism.
A dedicated CSRF token (double-submit cookie or synchronizer token) would be needed if cookies
ever had to be sent cross-site (`SameSite=None`) — not the case today.

## Brute-force protection: keyed by identifier, not by resolved account

After 5 failed logins for the same **identifier string** (not the resolved `user_id`) within 15
minutes, further attempts get a 429 for a cooldown window. Keying by the raw string the client
sent — rather than by whether it resolves to a real account — is deliberate: if lockout only
applied to real accounts, an attacker could tell a real username from a made-up one just by
whether the 6th attempt returns 429 or a plain 401 forever. This way lockout behaves identically
either way.

## Enumeration trade-offs

- **Login** is enumeration-resistant by design: unknown identifier and wrong password return the
  identical 401 + message, and a dummy Argon2 verification runs when the identifier doesn't
  resolve to a user, so response timing doesn't leak which case happened either.
- **Registration does reveal** whether a username or email is already taken (409, field-specific).
  This is a deliberate, accepted trade-off: signup forms conventionally do this (users expect to
  be told "that username is taken"), the UX cost of a vaguer error is high, and the information
  leaked is narrow (an account with that identifier exists at all — not login details).

## Known limitations / next steps

- **Email confirmation** is designed for but not built: `users.email_verified_at` exists (nullable,
  always `NULL` today), `/api/v1/me` already returns a derived `email_verified` boolean, and
  `register_user` in `app/services/auth_service.py` has a marked spot (right after the user is
  committed) where sending a verification email slots in without changing the endpoint's request
  or response contract. Login/app access are not gated on it yet.
- **Password reset by email** is not designed yet beyond "will need a signed, single-use token,
  which is the first real reason to introduce a `SECRET_KEY`."
- **No breached-password denylist** (e.g. HaveIBeenPwned k-anonymity check) yet.
- **No "active sessions" / "log out everywhere" UI** yet, though `sessions.last_used_at` and
  `created_at` already carry what that UI would need.
