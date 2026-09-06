"""Database repository for journal entries and embeddings."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from journal_search.core.models import (
    Embedding,
    EntryMetadata,
    JournalEntry,
    ProcessingStatus,
)


class EntryRepository:
    """Repository for journal entries and embeddings."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_entry(
        self,
        user_id: UUID,
        storage_path: str,
        metadata: EntryMetadata,
    ) -> JournalEntry:
        """Create a new journal entry."""
        entry_id = uuid4()
        now = datetime.utcnow()

        await self._session.execute(
            text("""
                INSERT INTO entries (
                    id, user_id, storage_path, journal_date, tags, notes,
                    processing_status, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :storage_path, :journal_date, :tags, :notes,
                    :processing_status, :created_at, :updated_at
                )
            """),
            {
                "id": entry_id,
                "user_id": user_id,
                "storage_path": storage_path,
                "journal_date": metadata.journal_date,
                "tags": metadata.tags,
                "notes": metadata.notes,
                "processing_status": ProcessingStatus.PENDING.value,
                "created_at": now,
                "updated_at": now,
            },
        )
        await self._session.commit()

        return JournalEntry(
            id=entry_id,
            user_id=user_id,
            storage_path=storage_path,
            journal_date=metadata.journal_date,
            tags=metadata.tags,
            notes=metadata.notes,
            processing_status=ProcessingStatus.PENDING,
            created_at=now,
            updated_at=now,
        )

    async def get_entry(self, entry_id: UUID, user_id: UUID) -> JournalEntry | None:
        """Get an entry by ID, scoped to user."""
        result = await self._session.execute(
            text("""
                SELECT id, user_id, storage_path, extracted_text, ocr_model,
                       ocr_confidence, journal_date, tags, notes, processing_status,
                       error_message, created_at, updated_at
                FROM entries
                WHERE id = :id AND user_id = :user_id
            """),
            {"id": entry_id, "user_id": user_id},
        )
        row = result.mappings().first()
        if not row:
            return None

        return JournalEntry(
            id=row["id"],
            user_id=row["user_id"],
            storage_path=row["storage_path"],
            extracted_text=row["extracted_text"],
            ocr_model=row["ocr_model"],
            ocr_confidence=row["ocr_confidence"],
            journal_date=row["journal_date"],
            tags=row["tags"] or [],
            notes=row["notes"],
            processing_status=ProcessingStatus(row["processing_status"]),
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def update_entry_ocr(
        self,
        entry_id: UUID,
        extracted_text: str,
        ocr_model: str,
        ocr_confidence: float | None,
    ) -> None:
        """Update entry with OCR results."""
        await self._session.execute(
            text("""
                UPDATE entries
                SET extracted_text = :text,
                    ocr_model = :model,
                    ocr_confidence = :confidence,
                    processing_status = :status,
                    updated_at = :updated_at
                WHERE id = :id
            """),
            {
                "id": entry_id,
                "text": extracted_text,
                "model": ocr_model,
                "confidence": ocr_confidence,
                "status": ProcessingStatus.PROCESSING.value,
                "updated_at": datetime.utcnow(),
            },
        )
        await self._session.commit()

    async def update_extracted_text(self, entry_id: UUID, extracted_text: str) -> None:
        """Update only the extracted text (e.g. after LLM cleanup)."""
        await self._session.execute(
            text("""
                UPDATE entries
                SET extracted_text = :text,
                    updated_at = :updated_at
                WHERE id = :id
            """),
            {
                "id": entry_id,
                "text": extracted_text,
                "updated_at": datetime.utcnow(),
            },
        )
        await self._session.commit()

    async def update_entry_status(
        self,
        entry_id: UUID,
        status: ProcessingStatus,
        error_message: str | None = None,
    ) -> None:
        """Update entry processing status."""
        await self._session.execute(
            text("""
                UPDATE entries
                SET processing_status = :status,
                    error_message = :error,
                    updated_at = :updated_at
                WHERE id = :id
            """),
            {
                "id": entry_id,
                "status": status.value,
                "error": error_message,
                "updated_at": datetime.utcnow(),
            },
        )
        await self._session.commit()

    async def store_embeddings(
        self,
        entry_id: UUID,
        user_id: UUID,
        chunks: list[str],
        embeddings: list[list[float]],
        model: str,
    ) -> list[Embedding]:
        """Store embeddings for an entry."""
        now = datetime.utcnow()
        results: list[Embedding] = []

        for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            emb_id = uuid4()
            await self._session.execute(
                text("""
                    INSERT INTO embeddings (
                        id, entry_id, user_id, chunk_index, chunk_text,
                        embedding, model, created_at
                    ) VALUES (
                        :id, :entry_id, :user_id, :chunk_index, :chunk_text,
                        :embedding, :model, :created_at
                    )
                """),
                {
                    "id": emb_id,
                    "entry_id": entry_id,
                    "user_id": user_id,
                    "chunk_index": idx,
                    "chunk_text": chunk_text,
                    "embedding": embedding,
                    "model": model,
                    "created_at": now,
                },
            )

            results.append(
                Embedding(
                    id=emb_id,
                    entry_id=entry_id,
                    user_id=user_id,
                    chunk_index=idx,
                    chunk_text=chunk_text,
                    embedding=embedding,
                    model=model,
                    created_at=now,
                )
            )

        await self._session.commit()
        return results

    async def delete_embeddings_for_entry(self, entry_id: UUID) -> None:
        """Delete all embeddings for an entry (for reprocessing)."""
        await self._session.execute(
            text("DELETE FROM embeddings WHERE entry_id = :entry_id"),
            {"entry_id": entry_id},
        )
        await self._session.commit()

    async def list_entries(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[JournalEntry]:
        """List entries for a user."""
        result = await self._session.execute(
            text("""
                SELECT id, user_id, storage_path, extracted_text, ocr_model,
                       ocr_confidence, journal_date, tags, notes, processing_status,
                       error_message, created_at, updated_at
                FROM entries
                WHERE user_id = :user_id
                ORDER BY journal_date DESC NULLS LAST, created_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"user_id": user_id, "limit": limit, "offset": offset},
        )

        return [
            JournalEntry(
                id=row["id"],
                user_id=row["user_id"],
                storage_path=row["storage_path"],
                extracted_text=row["extracted_text"],
                ocr_model=row["ocr_model"],
                ocr_confidence=row["ocr_confidence"],
                journal_date=row["journal_date"],
                tags=row["tags"] or [],
                notes=row["notes"],
                processing_status=ProcessingStatus(row["processing_status"]),
                error_message=row["error_message"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in result.mappings()
        ]
