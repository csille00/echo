"""Supabase Storage adapter."""

from datetime import datetime
from uuid import UUID

from echo.adapters.supabase.client import SupabaseClient


class SupabaseStorage:
    """Object storage backed by Supabase Storage."""

    def __init__(self, supabase: SupabaseClient) -> None:
        self._client = supabase.client
        self._bucket = supabase.storage_bucket

    async def upload(
        self,
        user_id: UUID,
        file_data: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        storage_path = f"{user_id}/{timestamp}_{filename}"

        await self._client.storage.from_(self._bucket).upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": content_type},
        )

        return storage_path

    async def download(self, storage_path: str) -> bytes:
        return await self._client.storage.from_(self._bucket).download(storage_path)

    async def get_public_url(self, storage_path: str) -> str:
        return self._client.storage.from_(self._bucket).get_public_url(storage_path)

    async def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> str:
        signed = await self._client.storage.from_(self._bucket).create_signed_url(
            storage_path,
            expires_in,
        )
        url = signed.get("signedURL") or signed.get("signedUrl")
        if not url:
            raise ValueError("Could not create signed URL")
        return url

    async def delete(self, storage_path: str) -> None:
        await self._client.storage.from_(self._bucket).remove([storage_path])
