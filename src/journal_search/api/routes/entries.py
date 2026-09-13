"""Journal entry routes."""

from collections.abc import AsyncIterator
from datetime import date
from typing import Annotated
from uuid import UUID

from dbos import DBOS
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from journal_search.adapters.db.repository import EntryRepository
from journal_search.api.deps.auth import CurrentUser
from journal_search.core.models import EntryMetadata, JournalEntry, ProcessingStatus
from journal_search.db.session import get_session
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
