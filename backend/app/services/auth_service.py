"""Authentication use-cases: register, login, refresh rotation, logout.

Orchestrates domain rules + repositories + security primitives. Contains no HTTP
concerns — raises :mod:`app.core.exceptions` errors instead.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.domain.identity.enums import DEFAULT_ROLE, SubscriptionPlan, SubscriptionStatus
from app.models.user import Session, Subscription, User
from app.repositories.session import SessionRepository
from app.repositories.user import UserRepository
from app.schemas.auth import RegisterRequest, TokenPair


class AuthService:
    def __init__(self, users: UserRepository, sessions: SessionRepository) -> None:
        self._users = users
        self._sessions = sessions

    # ── Registration ────────────────────────────────────────────────
    async def register(self, data: RegisterRequest) -> User:
        email = data.email.lower().strip()
        if await self._users.email_exists(email):
            raise ConflictError("An account with this email already exists.")

        role = await self._users.get_or_create_role(DEFAULT_ROLE)
        user = User(
            email=email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            target_role=data.target_role,
            is_active=True,
            roles=[role],
            subscription=Subscription(
                plan=SubscriptionPlan.FREE, status=SubscriptionStatus.ACTIVE, seats=1
            ),
        )
        return await self._users.add(user)

    # ── Login ────────────────────────────────────────────────────────
    async def authenticate(self, email: str, password: str) -> User:
        user = await self._users.get_by_email(email.lower().strip())
        # Constant-ish failure path: still verify against a dummy to limit timing leaks.
        if user is None or user.hashed_password is None:
            verify_password(password, hash_password("dummy-to-equalize-timing"))
            raise AuthenticationError("Invalid email or password.")
        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password.")
        if not user.is_active:
            raise AuthenticationError("Account is disabled.")
        return user

    # ── Token issuance ───────────────────────────────────────────────
    async def issue_tokens(
        self, user: User, *, user_agent: str | None = None, ip: str | None = None
    ) -> TokenPair:
        access = create_access_token(
            str(user.id),
            extra={"roles": [r.value for r in user.role_names], "email": user.email},
        )
        refresh, _jti = create_refresh_token(str(user.id))
        await self._sessions.add(
            Session(
                user_id=user.id,
                refresh_token_hash=hash_token(refresh),
                user_agent=user_agent,
                ip=ip,
                expires_at=datetime.now(UTC)
                + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            )
        )
        return TokenPair(access_token=access, refresh_token=refresh)

    # ── Refresh (rotation) ───────────────────────────────────────────
    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = jwt.decode(
                refresh_token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationError("Invalid or expired refresh token.") from exc

        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type.")

        record = await self._sessions.get_active_by_hash(hash_token(refresh_token))
        if record is None:
            raise AuthenticationError("Refresh token has been revoked or is unknown.")

        user = await self._users.get(record.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Account is no longer active.")

        # Rotate: revoke the presented token, issue a fresh pair.
        await self._sessions.revoke(record.id)
        return await self.issue_tokens(user)

    # ── Logout ───────────────────────────────────────────────────────
    async def logout(self, refresh_token: str) -> None:
        record = await self._sessions.get_active_by_hash(hash_token(refresh_token))
        if record is not None:
            await self._sessions.revoke(record.id)
