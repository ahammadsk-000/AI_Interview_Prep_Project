"""User profile + admin user-management endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.v1.deps import CurrentUser, UserRepo, require_roles
from app.domain.identity.enums import RoleName
from app.schemas.user import UserPublic, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
async def read_me(current: CurrentUser) -> UserPublic:
    return UserPublic.from_orm_user(current)


@router.patch("/me", response_model=UserPublic)
async def update_me(payload: UserUpdate, current: CurrentUser) -> UserPublic:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current, field, value)
    return UserPublic.from_orm_user(current)


@router.get(
    "",
    response_model=list[UserPublic],
    dependencies=[Depends(require_roles(RoleName.ADMIN))],
)
async def list_users(
    users: UserRepo,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[UserPublic]:
    """Admin-only: paginated user directory."""
    records = await users.list(limit=limit, offset=offset)
    return [UserPublic.from_orm_user(u) for u in records]
