"""Journal entry routes."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from journal_search.adapters.db.repository import EntryRepository
from journal_search.config import get_settings
from journal_search.core.models import EntryMetadata, JournalEntry, ProcessingStatus
from journal_search.workflows.process_entry import process_journal_entry

router = APIRouter(prefix="/entries", tags=["entries"])


# Request/Response models
class EntryResponse(BaseModel):
    id: UUID
    storage_path: str
    extracted_text: str | None
    journal_date: date | None
    tags: list[str]
    processing_status: ProcessingStatus
    created_at: str

    @classmethod
    def from_entry(cls, entry: JournalEntry) -> "EntryResponse":
        return cls(
            id=entry.id,
            storage_path=entry.storage_path,
            extracted_text=entry.extracted_text,
            journal_date=entry.journal_date,
            tags=entry.tags,
            processing_status=entry.processing_status,
            created_at=entry.created_at.isoformat(),
        )


class UploadResponse(BaseModel):
    entry_id: str
    message: str


# Placeholder for auth - replace with real auth
async def get_current_user_id(request: Request) -> UUID:
    """
    Get the current user ID from the request.

    TODO: Replace with real authentication (Supabase Auth, etc.)
    """
    # For development, check for X-User-ID header
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Set X-User-ID header for development.",
        )
    try:
        return UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format") from None


CurrentUser = Annotated[UUID, Depends(get_current_user_id)]


@router.post("/upload", response_model=UploadResponse)
async def upload_entry(
    user_id: CurrentUser,
    file: UploadFile = File(...),
    journal_date: date | None = Form(None),
    tags: str = Form(""),  # Comma-separated
    notes: str | None = Form(None),
) -> UploadResponse:
    """
    Upload a journal page image for processing.

    The image will be processed asynchronously:
    1. Stored in Supabase storage
    2. OCR extracted
    3. Text embedded for search
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Read file content
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    # Parse tags
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    # Create metadata
    metadata = EntryMetadata(
        journal_date=journal_date,
        tags=tag_list,
        notes=notes,
    )

    # Start the workflow
    entry_id = await process_journal_entry(
        image_data=content,
        user_id=user_id,
        filename=file.filename or "upload.jpg",
        content_type=file.content_type,
        metadata=metadata.model_dump(mode="json"),
    )

    return UploadResponse(
        entry_id=entry_id,
        message="Upload successful. Processing started.",
    )


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(
    entry_id: UUID,
    user_id: CurrentUser,
    request: Request,
) -> EntryResponse:
    """Get a single journal entry."""
    settings = get_settings()
    engine = create_async_engine(str(settings.database_url))

    async with AsyncSession(engine) as session:
        repo = EntryRepository(session)
        entry = await repo.get_entry(entry_id, user_id)

    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    return EntryResponse.from_entry(entry)


@router.get("/", response_model=list[EntryResponse])
async def list_entries(
    user_id: CurrentUser,
    request: Request,
    limit: int = 50,
    offset: int = 0,
) -> list[EntryResponse]:
    """List journal entries for the current user."""
    settings = get_settings()
    engine = create_async_engine(str(settings.database_url))

    async with AsyncSession(engine) as session:
        repo = EntryRepository(session)
        entries = await repo.list_entries(user_id, limit=limit, offset=offset)

    return [EntryResponse.from_entry(e) for e in entries]
