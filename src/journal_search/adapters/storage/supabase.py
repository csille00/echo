"""Supabase storage adapter."""

from datetime import datetime
from uuid import UUID

from supabase import AsyncClient


class SupabaseStorage:
    """Storage provider using Supabase Storage."""

    def __init__(self, client: AsyncClient, bucket: str = "journal-pages") -> None:
        self._client = client
        self._bucket = bucket

    async def upload(
        self,
        user_id: UUID,
        file_data: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        """
        Upload a file to Supabase storage.

        Files are namespaced by user_id to ensure isolation.
        """
        # Create path: {user_id}/{timestamp}_{filename}
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        storage_path = f"{user_id}/{timestamp}_{filename}"

        await self._client.storage.from_(self._bucket).upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": content_type},
        )

        return storage_path

    async def download(self, storage_path: str) -> bytes:
        """Download a file from Supabase storage."""
        response = await self._client.storage.from_(self._bucket).download(storage_path)
        return response

    async def get_public_url(self, storage_path: str) -> str:
        """Get a public URL for a file."""
        response = self._client.storage.from_(self._bucket).get_public_url(storage_path)
        return response

    async def get_signed_url(self, storage_path: str, expires_in: int = 3600) -> str:
        """Get a signed URL for private file access."""
        response = await self._client.storage.from_(self._bucket).create_signed_url(
            storage_path, expires_in
        )
        return response["signedURL"]

    async def delete(self, storage_path: str) -> None:
        """Delete a file from Supabase storage."""
        await self._client.storage.from_(self._bucket).remove([storage_path])
