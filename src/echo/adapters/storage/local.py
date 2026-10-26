"""Local filesystem storage adapter for development."""

import asyncio
from datetime import datetime
from pathlib import Path
from uuid import UUID


def safe_storage_name(filename: str) -> str:
    """Keep only the base filename so uploads cannot escape the storage root."""
    name = Path(filename).name.replace("\x00", "")
    if name in {"", ".", ".."}:
        return "upload"
    return name


class LocalFilesystemStorage:
    """Store uploads on the local filesystem."""

    def __init__(self, root: str | Path = "data/uploads") -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    def _destination(self, storage_path: str) -> Path:
        root = self._root.resolve()
        dest = (root / storage_path).resolve()
        if not dest.is_relative_to(root):
            raise ValueError("Invalid storage path")
        return dest

    async def upload(
        self,
        user_id: UUID,
        file_data: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        storage_path = f"{user_id}/{timestamp}_{safe_storage_name(filename)}"
        dest = self._destination(storage_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(dest.write_bytes, file_data)
        return storage_path

    async def download(self, storage_path: str) -> bytes:
        dest = self._destination(storage_path)
        return await asyncio.to_thread(dest.read_bytes)

    async def get_public_url(self, storage_path: str) -> str:
        raise NotImplementedError("Local storage is served by the API")

    async def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> str:
        raise NotImplementedError("Local storage is served by the API")

    async def delete(self, storage_path: str) -> None:
        path = self._destination(storage_path)
        if path.exists():
            await asyncio.to_thread(path.unlink)
