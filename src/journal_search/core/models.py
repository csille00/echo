"""Core domain models."""

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class ProcessingStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EntryMetadata(BaseModel):
    """User-provided metadata for a journal entry."""

    journal_date: date | None = Field(
        default=None,
        description="Date the journal entry was written",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="User-provided tags",
    )
    notes: str | None = Field(
        default=None,
        description="Additional notes about the entry",
    )


class JournalEntry(BaseModel):
    """A journal entry with extracted text and metadata."""

    id: UUID
    user_id: UUID  # Always required - user isolation is non-negotiable
    storage_path: str
    extracted_text: str | None = None
    ocr_model: str | None = None
    ocr_confidence: float | None = None
    journal_date: date | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class Embedding(BaseModel):
    """A text embedding for semantic search."""

    id: UUID
    entry_id: UUID
    user_id: UUID  # Denormalized for efficient filtered queries
    chunk_index: int = 0
    chunk_text: str
    embedding: list[float]
    model: str
    created_at: datetime


class OCRResult(BaseModel):
    """Result from OCR extraction."""

    text: str
    confidence: float | None = None
    model: str


class EmbeddingResult(BaseModel):
    """Result from embedding generation."""

    embedding: list[float]
    model: str
    token_count: int | None = None


class TextCleanupResult(BaseModel):
    """Result from LLM post-processing of OCR text."""

    text: str
    model: str
    source_model: str | None = Field(
        default=None,
        description="OCR model that produced the input text",
    )
