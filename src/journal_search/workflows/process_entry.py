"""Journal entry processing workflow."""

from uuid import UUID

from dbos import DBOS

from journal_search.core.models import EntryMetadata, ProcessingStatus
from journal_search.dependencies import get_embedder, get_ocr, get_repository, get_storage


@DBOS.workflow()
async def process_journal_entry(
    image_data: bytes,
    user_id: UUID,
    filename: str,
    content_type: str,
    metadata: dict,  # Serialized EntryMetadata
) -> str:
    """
    Process a journal entry through the full pipeline.

    Steps:
    1. Upload image to storage
    2. Create entry record
    3. Extract text via OCR
    4. Generate embeddings
    5. Store embeddings

    Each step is checkpointed by DBOS for durability.
    """
    entry_metadata = EntryMetadata(**metadata)

    # Step 1: Upload to storage
    storage_path = await upload_image_step(user_id, image_data, filename, content_type)

    # Step 2: Create entry record
    entry_id = await create_entry_step(user_id, storage_path, entry_metadata)

    # Step 3: OCR extraction
    try:
        extracted_text = await ocr_extract_step(entry_id, image_data)
    except Exception as e:
        await mark_failed_step(entry_id, str(e))
        raise

    # Step 4 & 5: Embed and store
    try:
        await embed_and_store_step(entry_id, user_id, extracted_text)
    except Exception as e:
        await mark_failed_step(entry_id, str(e))
        raise

    # Mark complete
    await mark_complete_step(entry_id)

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
async def create_entry_step(
    user_id: UUID,
    storage_path: str,
    metadata: EntryMetadata,
) -> UUID:
    """Create entry record - checkpointed."""
    repo = get_repository()
    entry = await repo.create_entry(user_id, storage_path, metadata)
    return entry.id


@DBOS.step()
async def ocr_extract_step(entry_id: UUID, image_data: bytes) -> str:
    """Extract text via OCR - checkpointed and retryable."""
    ocr = get_ocr()
    repo = get_repository()

    result = await ocr.extract(image_data)

    await repo.update_entry_ocr(
        entry_id=entry_id,
        extracted_text=result.text,
        ocr_model=result.model,
        ocr_confidence=result.confidence,
    )

    return result.text


@DBOS.step()
async def embed_and_store_step(entry_id: UUID, user_id: UUID, text: str) -> None:
    """Generate and store embeddings - checkpointed."""
    embedder = get_embedder()
    repo = get_repository()

    # For now, embed the whole text as one chunk
    # TODO: Implement chunking for long entries
    chunks = [text] if text.strip() else []

    if chunks:
        results = await embedder.embed_batch(chunks)
        embeddings = [r.embedding for r in results]
        model = results[0].model if results else embedder.name

        await repo.store_embeddings(
            entry_id=entry_id,
            user_id=user_id,
            chunks=chunks,
            embeddings=embeddings,
            model=model,
        )


@DBOS.step()
async def mark_failed_step(entry_id: UUID, error_message: str) -> None:
    """Mark entry as failed - checkpointed."""
    repo = get_repository()
    await repo.update_entry_status(entry_id, ProcessingStatus.FAILED, error_message)


@DBOS.step()
async def mark_complete_step(entry_id: UUID) -> None:
    """Mark entry as complete - checkpointed."""
    repo = get_repository()
    await repo.update_entry_status(entry_id, ProcessingStatus.COMPLETED)
