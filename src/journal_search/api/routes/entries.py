"""Journal entry routes."""

from collections.abc import AsyncIterator
from datetime import date
from typing import Annotated
from uuid import UUID

from dbos import DBOS
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from journal_search.adapters.db.repository import EntryRepository
from journal_search.api.deps.auth import CurrentUser
from journal_search.core.models import EntryMetadata, JournalEntry, ProcessingStatus
from journal_search.db.session import get_session
from journal_search.dependencies import get_storage
from journal_search.workflows.process_entry import process_journal_entry

router = APIRouter(prefix="/entries", tags=["entries"])


async def db_session() -> AsyncIterator[AsyncSession]:
    """Yield a database session for the request."""
    async with get_session() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(db_session)]


# Request/Response models
class EntryResponse(BaseModel):
    id: UUID
    storage_path: str
    extracted_text: str | None
    journal_date: date | None
    tags: list[str]
    notes: str | None = None
    processing_status: ProcessingStatus
    error_message: str | None = None
    created_at: str
    updated_at: str

    @classmethod
    def from_entry(cls, entry: JournalEntry) -> "EntryResponse":
        return cls(
            id=entry.id,
            storage_path=entry.storage_path,
            extracted_text=entry.extracted_text,
            journal_date=entry.journal_date,
            tags=entry.tags,
            notes=entry.notes,
            processing_status=entry.processing_status,
            error_message=entry.error_message,
            created_at=entry.created_at.isoformat(),
            updated_at=entry.updated_at.isoformat(),
        )


class EntryUpdateRequest(BaseModel):
    journal_date: date | None = None
    clear_journal_date: bool = False
    extracted_text: str | None = None
    tags: list[str] | None = None
    notes: str | None = None


class EntryImageUrlResponse(BaseModel):
    url: str
    expires_in: int | None = Field(default=None, description="Seconds until expiry for signed URLs")


class UploadResponse(BaseModel):
    entry_id: str
    message: str


@router.post("/upload", response_model=UploadResponse)
async def upload_entry(
    user_id: CurrentUser,
    session: DbSession,
    file: UploadFile = File(...),
    journal_date: date | None = Form(None),
    tags: str = Form(""),  # Comma-separated
    notes: str | None = Form(None),
) -> UploadResponse:
    """
    Upload a journal page image for processing.

    Returns immediately after creating a pending entry and starting the
    DBOS workflow. Poll GET /entries/{entry_id} for processing status.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    metadata = EntryMetadata(
        journal_date=journal_date,
        tags=tag_list,
        notes=notes,
    )

    repo = EntryRepository(session)
    entry = await repo.create_pending_entry(user_id, metadata)

    await DBOS.start_workflow_async(
        process_journal_entry,
        entry.id,
        user_id,
        content,
        file.filename or "upload.jpg",
        file.content_type,
    )

    return UploadResponse(
        entry_id=str(entry.id),
        message="Upload successful. Processing started.",
    )


@router.get("/{entry_id}/image")
async def get_entry_image(
    entry_id: UUID,
    user_id: CurrentUser,
    session: DbSession,
) -> Response:
    """Stream the entry image (use with Authorization header)."""
    repo = EntryRepository(session)
    entry = await repo.get_entry(entry_id, user_id)
    if not entry or entry.storage_path.startswith("pending/"):
        raise HTTPException(status_code=404, detail="Image not available")

    storage = get_storage()
    data = await storage.download(entry.storage_path)
    return Response(content=data, media_type="image/jpeg")


@router.get("/{entry_id}/image-url", response_model=EntryImageUrlResponse)
async def get_entry_image_url(
    entry_id: UUID,
    user_id: CurrentUser,
    session: DbSession,
) -> EntryImageUrlResponse:
    """Return a URL to view the entry image (signed when using private storage)."""
    repo = EntryRepository(session)
    entry = await repo.get_entry(entry_id, user_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if entry.storage_path.startswith("pending/"):
        raise HTTPException(status_code=404, detail="Image not available yet")

    storage = get_storage()
    try:
        url = await storage.get_signed_url(entry.storage_path, 3600)
    except (ValueError, NotImplementedError) as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return EntryImageUrlResponse(url=url, expires_in=3600)


@router.patch("/{entry_id}", response_model=EntryResponse)
async def update_entry(
    entry_id: UUID,
    body: EntryUpdateRequest,
    user_id: CurrentUser,
    session: DbSession,
) -> EntryResponse:
    """Update journal date, recognized text, tags, or notes."""
    repo = EntryRepository(session)
    entry = await repo.update_entry_fields(
        entry_id,
        user_id,
        journal_date=body.journal_date,
        extracted_text=body.extracted_text,
        tags=body.tags,
        notes=body.notes,
        clear_journal_date=body.clear_journal_date,
    )
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return EntryResponse.from_entry(entry)


@router.get("/{entry_id}", response_model=EntryResponse)
async def get_entry(
    entry_id: UUID,
    user_id: CurrentUser,
    session: DbSession,
) -> EntryResponse:
    """Get a single journal entry."""
    repo = EntryRepository(session)
    entry = await repo.get_entry(entry_id, user_id)

    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    return EntryResponse.from_entry(entry)


@router.get("/", response_model=list[EntryResponse])
async def list_entries(
    user_id: CurrentUser,
    session: DbSession,
    limit: int = 50,
    offset: int = 0,
) -> list[EntryResponse]:
    """List journal entries for the current user."""
    repo = EntryRepository(session)
    entries = await repo.list_entries(user_id, limit=limit, offset=offset)
    return [EntryResponse.from_entry(e) for e in entries]
