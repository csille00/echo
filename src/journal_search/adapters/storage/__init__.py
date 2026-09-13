"""Storage adapter implementations."""

from journal_search.adapters.storage.factory import create_storage_provider
from journal_search.adapters.storage.local import LocalFilesystemStorage

__all__ = ["LocalFilesystemStorage", "create_storage_provider"]
