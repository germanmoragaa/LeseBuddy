import hashlib
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
