"""Storage Provider interface."""

from typing import Protocol
from uuid import UUID


class StorageProvider(Protocol):
    """Interface for file storage services."""

    async def upload(
        self,
        user_id: UUID,
        file_data: bytes,
        filename: str,
        content_type: str,
    ) -> str:
        """
        Upload a file to storage.

        Args:
            user_id: Owner of the file (for path namespacing)
            file_data: Raw file bytes
            filename: Original filename
            content_type: MIME type

        Returns:
            Storage path/key for the uploaded file
        """
        ...

    async def download(self, storage_path: str) -> bytes:
        """
        Download a file from storage.

        Args:
            storage_path: Path returned from upload

        Returns:
            Raw file bytes
        """
        ...

    async def get_public_url(self, storage_path: str) -> str:
        """
        Get a public/signed URL for a file.

        Args:
            storage_path: Path returned from upload

        Returns:
            URL to access the file
        """
        ...

    async def delete(self, storage_path: str) -> None:
        """
        Delete a file from storage.

        Args:
            storage_path: Path returned from upload
        """
        ...
