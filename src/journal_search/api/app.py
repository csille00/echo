"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dbos import DBOS
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import acreate_client

from journal_search.adapters.storage.supabase import SupabaseStorage
from journal_search.api.routes import entries
from journal_search.config import Settings, get_settings
from journal_search.dependencies import (
    Container,
    create_embedding_provider_from_settings,
    create_ocr_provider_from_settings,
    create_text_cleanup_provider_from_settings,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan - setup and teardown."""
    settings = get_settings()

    supabase = await acreate_client(
        settings.supabase_url,
        settings.supabase_key.get_secret_value(),
    )

    ocr = create_ocr_provider_from_settings(settings)
    embedder = create_embedding_provider_from_settings(settings)
    storage = SupabaseStorage(supabase, settings.supabase_storage_bucket)
    text_cleanup = create_text_cleanup_provider_from_settings(settings)

    container = Container(
        ocr=ocr,
        embedder=embedder,
        storage=storage,
        text_cleanup=text_cleanup,
    )
    container.install()

    app.state.supabase = supabase
    app.state.container = container

    DBOS.launch()

    yield

    await container.close()
    DBOS.destroy()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="Journal Search",
        description="AI-powered journal OCR and search",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(entries.router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
