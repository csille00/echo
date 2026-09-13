"""Journal entry processing workflow."""

from uuid import UUID

from dbos import DBOS

from journal_search.adapters.db.repository import EntryRepository
from journal_search.core.models import ProcessingStatus
from journal_search.db.session import get_session
from journal_search.dependencies import (
    get_embedder,
    get_ocr,
    get_realtime,
    get_storage,
    get_text_cleanup,
)


@DBOS.workflow()
async def process_journal_entry(
    entry_id: UUID,
    user_id: UUID,
    image_data: bytes,
    filename: str,
    content_type: str,
) -> str:
    """
    Process a journal entry through the full pipeline.

    Steps:
    1. Upload image to storage
    2. Update entry storage path
    3. Extract text via OCR
    4. Optional LLM cleanup
    5. Generate and store embeddings
    6. Mark complete

    Each step is checkpointed by DBOS for durability.
    """
    storage_path = await upload_image_step(user_id, image_data, filename, content_type)
    await update_storage_path_step(entry_id, storage_path)

    try:
        extracted_text, ocr_model = await ocr_extract_step(entry_id, image_data)
    except Exception as e:
        await mark_failed_step(entry_id, user_id, str(e))
        raise

    cleanup = get_text_cleanup()
    if cleanup is not None:
        try:
            extracted_text = await text_cleanup_step(extracted_text, ocr_model)
            await update_entry_text_step(entry_id, extracted_text)
        except Exception as e:
            await mark_failed_step(entry_id, user_id, str(e))
            raise

    try:
        await embed_and_store_step(entry_id, user_id, extracted_text)
    except Exception as e:
        await mark_failed_step(entry_id, user_id, str(e))
        raise

    await mark_complete_step(entry_id, user_id)
    return str(entry_id)


@DBOS.step()
async def upload_image_step(
    user_id: UUID,
    image_data: bytes,
    filename: str,
    content_type: str,
) -> str:
    """Upload image to storage - checkpointed."""
    storage = get_storage()
    return await storage.upload(user_id, image_data, filename, content_type)


@DBOS.step()
async def update_storage_path_step(entry_id: UUID, storage_path: str) -> None:
    """Persist the storage path after upload."""
    async with get_session() as session:
        repo = EntryRepository(session)
        await repo.update_storage_path(entry_id, storage_path)


@DBOS.step()
async def ocr_extract_step(entry_id: UUID, image_data: bytes) -> tuple[str, str]:
    """Extract text via OCR - checkpointed and retryable."""
    ocr = get_ocr()
    result = await ocr.extract(image_data)

    async with get_session() as session:
        repo = EntryRepository(session)
        await repo.update_entry_ocr(
            entry_id=entry_id,
            extracted_text=result.text,
            ocr_model=result.model,
            ocr_confidence=result.confidence,
        )

    return result.text, result.model


@DBOS.step()
async def text_cleanup_step(raw_text: str, source_model: str) -> str:
    """Clean OCR text with an LLM - checkpointed and retryable."""
    cleanup = get_text_cleanup()
    if cleanup is None:
        return raw_text

    result = await cleanup.cleanup(raw_text, source_model=source_model)
    return result.text


@DBOS.step()
async def update_entry_text_step(entry_id: UUID, extracted_text: str) -> None:
    """Persist cleaned text after LLM post-processing."""
    async with get_session() as session:
        repo = EntryRepository(session)
        await repo.update_extracted_text(entry_id, extracted_text)


@DBOS.step()
async def embed_and_store_step(entry_id: UUID, user_id: UUID, text: str) -> None:
    """Generate and store embeddings - checkpointed."""
    embedder = get_embedder()
    chunks = [text] if text.strip() else []

    if not chunks:
        return

    results = await embedder.embed_batch(chunks)
    embeddings = [r.embedding for r in results]
    model = results[0].model if results else embedder.name

    async with get_session() as session:
        repo = EntryRepository(session)
        await repo.store_embeddings(
            entry_id=entry_id,
            user_id=user_id,
            chunks=chunks,
            embeddings=embeddings,
            model=model,
        )


@DBOS.step()
async def mark_failed_step(entry_id: UUID, user_id: UUID, error_message: str) -> None:
    """Mark entry as failed - checkpointed."""
    async with get_session() as session:
        repo = EntryRepository(session)
        await repo.update_entry_status(entry_id, ProcessingStatus.FAILED, error_message)

    await get_realtime().notify_entry_status(entry_id, user_id, ProcessingStatus.FAILED)


@DBOS.step()
async def mark_complete_step(entry_id: UUID, user_id: UUID) -> None:
    """Mark entry as complete - checkpointed."""
    async with get_session() as session:
        repo = EntryRepository(session)
        await repo.update_entry_status(entry_id, ProcessingStatus.COMPLETED)

    await get_realtime().notify_entry_status(entry_id, user_id, ProcessingStatus.COMPLETED)
