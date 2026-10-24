"""Database repository for journal entries and embeddings."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from journal_search.core.models import (
    Embedding,
    EntryMetadata,
    JournalEntry,
    ProcessingStatus,
    SearchResult,
)


class EntryRepository:
    """Repository for journal entries and embeddings."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pending_entry(
        self,
        user_id: UUID,
        metadata: EntryMetadata,
    ) -> JournalEntry:
        """Create a journal entry before async processing starts."""
        entry_id = uuid4()
        storage_path = f"pending/{entry_id}"
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

    async def update_storage_path(self, entry_id: UUID, storage_path: str) -> None:
        """Set the storage path after the image upload completes."""
        await self._session.execute(
            text("""
                UPDATE entries
                SET storage_path = :storage_path,
                    updated_at = :updated_at
                WHERE id = :id
            """),
            {
                "id": entry_id,
                "storage_path": storage_path,
                "updated_at": datetime.utcnow(),
            },
        )
        await self._session.commit()

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
            embedding_literal = "[" + ",".join(str(v) for v in embedding) + "]"
            await self._session.execute(
                text("""
                    INSERT INTO embeddings (
                        id, entry_id, user_id, chunk_index, chunk_text,
                        embedding, model, created_at
                    ) VALUES (
                        :id, :entry_id, :user_id, :chunk_index, :chunk_text,
                        CAST(:embedding AS vector), :model, :created_at
                    )
                """),
                {
                    "id": emb_id,
                    "entry_id": entry_id,
                    "user_id": user_id,
                    "chunk_index": idx,
                    "chunk_text": chunk_text,
                    "embedding": embedding_literal,
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

    async def update_entry_fields(
        self,
        entry_id: UUID,
        user_id: UUID,
        *,
        journal_date: date | None = None,
        extracted_text: str | None = None,
        tags: list[str] | None = None,
        notes: str | None = None,
        clear_journal_date: bool = False,
    ) -> JournalEntry | None:
        """Update user-editable fields on an entry."""
        entry = await self.get_entry(entry_id, user_id)
        if entry is None:
            return None

        new_date = None if clear_journal_date else (journal_date if journal_date is not None else entry.journal_date)
        new_text = extracted_text if extracted_text is not None else entry.extracted_text
        new_tags = tags if tags is not None else entry.tags
        new_notes = notes if notes is not None else entry.notes

        await self._session.execute(
            text("""
                UPDATE entries
                SET journal_date = :journal_date,
                    extracted_text = :extracted_text,
                    tags = :tags,
                    notes = :notes,
                    updated_at = :updated_at
                WHERE id = :id AND user_id = :user_id
            """),
            {
                "id": entry_id,
                "user_id": user_id,
                "journal_date": new_date,
                "extracted_text": new_text,
                "tags": new_tags,
                "notes": new_notes,
                "updated_at": datetime.utcnow(),
            },
        )
        await self._session.commit()
        return await self.get_entry(entry_id, user_id)

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

    async def search_similar(
        self,
        user_id: UUID,
        query_embedding: list[float],
        limit: int = 10,
    ) -> list[SearchResult]:
        """Find entries most similar to a query embedding (cosine distance)."""
        embedding_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"
        result = await self._session.execute(
            text("""
                SELECT
                    e.id AS entry_id,
                    e.journal_date,
                    e.tags,
                    emb.chunk_text,
                    1 - (emb.embedding <=> CAST(:query_embedding AS vector)) AS similarity
                FROM embeddings emb
                JOIN entries e ON e.id = emb.entry_id
                WHERE emb.user_id = :user_id
                  AND e.processing_status = :status
                ORDER BY emb.embedding <=> CAST(:query_embedding AS vector)
                LIMIT :limit
            """),
            {
                "user_id": user_id,
                "query_embedding": embedding_literal,
                "status": ProcessingStatus.COMPLETED.value,
                "limit": limit,
            },
        )

        return [
            SearchResult(
                entry_id=row["entry_id"],
                chunk_text=row["chunk_text"],
                similarity=float(row["similarity"]),
                journal_date=row["journal_date"],
                tags=row["tags"] or [],
            )
            for row in result.mappings()
        ]
