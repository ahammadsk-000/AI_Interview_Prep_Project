"""File storage port + local-disk implementation.

Services depend on the ``FileStorage`` Protocol; production swaps in an
S3/MinIO implementation (Phase 9) without touching call sites.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import settings


class FileStorage(Protocol):
    def save(self, *, namespace: str, filename: str, content: bytes) -> str: ...
    def read(self, storage_key: str) -> bytes: ...
    def delete(self, storage_key: str) -> None: ...


class LocalFileStorage:
    """Stores files under ``STORAGE_DIR/<namespace>/<uuid>_<filename>``."""

    def __init__(self, base_dir: str | None = None) -> None:
        self._base = Path(base_dir or settings.STORAGE_DIR)

    def save(self, *, namespace: str, filename: str, content: bytes) -> str:
        key = f"{namespace}/{uuid.uuid4().hex}_{filename}"
        path = self._base / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key

    def read(self, storage_key: str) -> bytes:
        return (self._base / storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        path = self._base / storage_key
        if path.exists():
            path.unlink()


def get_storage() -> FileStorage:
    return LocalFileStorage()
