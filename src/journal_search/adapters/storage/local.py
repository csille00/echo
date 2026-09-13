"""Local filesystem storage adapter for development."""

import asyncio
from datetime import datetime
from pathlib import Path
from uuid import UUID


class LocalFilesystemStorage:
    """Store uploads on the local filesystem."""

    def __init__(self, root: str | Path = "data/uploads") -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    async def upload(
        self,
        user_id: UUID,
        file_data: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        storage_path = f"{user_id}/{timestamp}_{filename}"
        dest = self._root / storage_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(dest.write_bytes, file_data)
        return storage_path

    async def download(self, storage_path: str) -> bytes:
        return await asyncio.to_thread((self._root / storage_path).read_bytes)

    async def get_public_url(self, storage_path: str) -> str:
        return (self._root / storage_path).as_uri()

    async def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> str:
        return await self.get_public_url(storage_path)

    async def delete(self, storage_path: str) -> None:
        path = self._root / storage_path
        if path.exists():
            await asyncio.to_thread(path.unlink)
