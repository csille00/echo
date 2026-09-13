"""Semantic search routes."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, Field

from journal_search.adapters.db.repository import EntryRepository
from journal_search.api.deps.auth import CurrentUser
from journal_search.core.models import SearchResult
from journal_search.dependencies import get_embedder

from .entries import DbSession

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=10, ge=1, le=50)


class SearchHitResponse(BaseModel):
    entry_id: UUID
    chunk_text: str
    similarity: float
    journal_date: date | None
    tags: list[str]

    @classmethod
    def from_result(cls, result: SearchResult) -> "SearchHitResponse":
        return cls(
            entry_id=result.entry_id,
            chunk_text=result.chunk_text,
            similarity=result.similarity,
            journal_date=result.journal_date,
            tags=result.tags,
        )


class SearchResponse(BaseModel):
    results: list[SearchHitResponse]


@router.post("/", response_model=SearchResponse)
async def search_entries(
    body: SearchRequest,
    user_id: CurrentUser,
    session: DbSession,
) -> SearchResponse:
    """Search journal entries by semantic similarity."""
    embedder = get_embedder()
    query_embedding = (await embedder.embed(body.query)).embedding

    repo = EntryRepository(session)
    results = await repo.search_similar(
        user_id=user_id,
        query_embedding=query_embedding,
        limit=body.limit,
    )
    return SearchResponse(results=[SearchHitResponse.from_result(r) for r in results])
