"""Password hashing and session token utilities.

Passwords use Argon2id via `pwdlib` -- a modern, memory-hard KDF designed
for low-entropy human-chosen secrets. Session tokens are the opposite case:
they are generated with `secrets.token_urlsafe`, so they already have very
high entropy, which is why a fast SHA-256 hash is an acceptable (and
appropriately cheap) way to store them -- SHA-256 must never be used for
passwords.
"""

import hashlib
import secrets

from pwdlib import PasswordHash

_password_hasher = PasswordHash.recommended()

# 32 bytes of `secrets` randomness, base64url-encoded to ~43 characters:
# comfortably beyond what's brute-forceable, consistent with common session
# token sizing guidance.
_SESSION_TOKEN_BYTES = 32


def hash_password(password: str) -> str:
    """Hash `password` with Argon2id for storage in `User.password_hash`."""

    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether `password` matches a previously hashed `password_hash`."""

    return _password_hasher.verify(password, password_hash)


def generate_session_token() -> str:
    """Generate a new, cryptographically secure, high-entropy session token.

    The raw value returned here is only ever placed in the HTTP-only cookie
    and used transiently to compute its hash -- it is never persisted.
    """

    return secrets.token_urlsafe(_SESSION_TOKEN_BYTES)


def hash_session_token(token: str) -> str:
    """Deterministically hash a raw session token for storage/lookup.

    SHA-256 (not Argon2id) is intentional and sufficient here: the input
    already has high entropy from `generate_session_token`, so this hash
    only needs to be deterministic and resistant to reversal, not slow.
    """

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
