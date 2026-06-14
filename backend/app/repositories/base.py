"""Abstract repository contract (Dependency Inversion).

Services depend on these Protocols, not on SQLAlchemy. Swapping the persistence
backend (or mocking in tests) requires only a new implementation.
"""
from __future__ import annotations

import uuid
from typing import Generic, Protocol, TypeVar

T = TypeVar("T")


class Repository(Protocol, Generic[T]):
    async def get(self, id_: uuid.UUID) -> T | None: ...
    async def add(self, entity: T) -> T: ...
    async def list(self, *, limit: int = 50, offset: int = 0) -> list[T]: ...
