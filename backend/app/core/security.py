"""Password hashing (Argon2id), password policy and JWT helpers."""
import hashlib
import re
import secrets
import uuid
from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings
from app.core.database import utcnow

# argon2-cffi's PasswordHasher is Argon2id by default. Tests use cheap parameters purely for speed;
# every other environment uses the library's recommended defaults.
_hasher = (
    PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1)
    if get_settings().environment == "test"
    else PasswordHasher()
)
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


_PASSWORD_RULES = [
    (r".{10,}", "at least 10 characters"),
    (r"[a-z]", "a lowercase letter"),
    (r"[A-Z]", "an uppercase letter"),
    (r"\d", "a digit"),
    (r"[^A-Za-z0-9]", "a special character"),
]


def password_policy_errors(password: str) -> list[str]:
    return [f"Password needs {msg}" for rx, msg in _PASSWORD_RULES if not re.search(rx, password)]


def create_access_token(user_id: uuid.UUID, session_id: uuid.UUID) -> str:
    s = get_settings()
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=s.access_token_minutes),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, s.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError on any problem (expired, tampered, wrong type)."""
    payload = jwt.decode(token, get_settings().secret_key, algorithms=[ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("wrong token type")
    return payload


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """Refresh tokens and OTPs are stored only as SHA-256 digests."""
    return hashlib.sha256(token.encode()).hexdigest()
