"""Authentication endpoints: register, login, refresh, logout."""
from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.api.v1.deps import AuthSvc
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.schemas.user import UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request, auth: AuthSvc) -> AuthResponse:
    user = await auth.register(payload)
    tokens = await auth.issue_tokens(
        user,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    return AuthResponse(user=UserPublic.from_orm_user(user), tokens=tokens)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, request: Request, auth: AuthSvc) -> AuthResponse:
    user = await auth.authenticate(payload.email, payload.password)
    tokens = await auth.issue_tokens(
        user,
        user_agent=request.headers.get("user-agent"),
        ip=request.client.host if request.client else None,
    )
    return AuthResponse(user=UserPublic.from_orm_user(user), tokens=tokens)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, auth: AuthSvc) -> TokenPair:
    return await auth.refresh(payload.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(payload: RefreshRequest, auth: AuthSvc) -> MessageResponse:
    await auth.logout(payload.refresh_token)
    return MessageResponse(message="Logged out.")
