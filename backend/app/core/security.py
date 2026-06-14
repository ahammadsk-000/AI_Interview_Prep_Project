"""Security primitives: password hashing (Argon2id) and JWT token handling."""
from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

# Production-strength Argon2id by default; cheap params under tests for speed
# (security is unaffected in real environments).
if settings.ENVIRONMENT == "test":
    _ph = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1)
else:
    _ph = PasswordHasher()

TokenType = Literal["access", "refresh"]


# ── Password hashing ────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def needs_rehash(hashed: str) -> bool:
    return _ph.check_needs_rehash(hashed)


# ── JWT ─────────────────────────────────────────────────────────────
def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    extra: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Returns (encoded_jwt, jti)."""
    now = datetime.now(UTC)
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    if extra:
        payload.update(extra)
    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded, jti


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    token, _ = _create_token(
        subject,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        extra,
    )
    return token


def create_refresh_token(subject: str) -> tuple[str, str]:
    """Returns (token, jti). The jti/hash is persisted server-side for rotation."""
    return _create_token(
        subject,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decodes & validates a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def hash_token(token: str) -> str:
    """Stable hash for storing refresh tokens at rest (never store raw)."""
    return hashlib.sha256(token.encode()).hexdigest()
