import hashlib
import hmac
import secrets

from pwdlib import PasswordHash

SESSION_COOKIE_NAME = "session_token"

_password_hash = PasswordHash.recommended()

# A real Argon2id hash of a fixed, known string. Verifying against this when an identifier
# doesn't resolve to a user keeps the login endpoint's response time roughly the same whether
# the account exists or not, so timing can't be used to enumerate accounts.
_DUMMY_PASSWORD_HASH = _password_hash.hash("not-a-real-password-used-only-for-timing")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def verify_dummy_password() -> None:
    """Call when an identifier doesn't match any user, to burn roughly the same time a real
    verification would take."""
    _password_hash.verify("irrelevant", _DUMMY_PASSWORD_HASH)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_verification_code() -> str:
    """A uniform random 6-digit code, zero-padded (e.g. "003492")."""
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_verification_code(code: str, secret_key: str) -> str:
    """HMAC, not a plain hash: a 6-digit code only has 1,000,000 possible values, so an
    unsalted/unkeyed hash of it would let anyone who reads the table brute-force the plaintext
    in microseconds. Keying it with the server's secret means that's no longer enough."""
    return hmac.new(secret_key.encode("utf-8"), code.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_verification_code(code: str, code_hash: str, secret_key: str) -> bool:
    return hmac.compare_digest(hash_verification_code(code, secret_key), code_hash)
