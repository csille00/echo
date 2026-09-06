"""FastAPI application factory."""

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dbos import DBOS
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from supabase import acreate_client

from journal_search.api.routes import entries
from journal_search.config import Settings, get_settings
from journal_search.dependencies import (
    Container,
    create_embedding_provider,
    create_ocr_provider,
)
from journal_search.adapters.storage.supabase import SupabaseStorage


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan - setup and teardown."""
    settings = get_settings()

    # Initialize Supabase client
    supabase = await acreate_client(
        settings.supabase_url,
        settings.supabase_key.get_secret_value(),
    )

    # Create providers based on config
    ocr_kwargs: dict[str, object] = {}
    if settings.ocr_provider.value == "google_vision":
        if settings.google_vision_api_key is not None:
            ocr_kwargs["api_key"] = settings.google_vision_api_key.get_secret_value()
        elif settings.google_vision_credentials_file is not None:
            ocr_kwargs["credentials_file"] = settings.google_vision_credentials_file
        elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            ocr_kwargs["credentials_file"] = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
        else:
            raise RuntimeError(
                "Google Vision credentials required. Set GOOGLE_VISION_API_KEY or "
                "GOOGLE_APPLICATION_CREDENTIALS."
            )

    ocr = create_ocr_provider(settings.ocr_provider.value, **ocr_kwargs)
    embedder = create_embedding_provider(
        settings.embedding_provider.value,
        model=settings.embedding_model,
        dimension=settings.embedding_dimension,
        base_url=settings.ollama_base_url,
    )
    storage = SupabaseStorage(supabase, settings.supabase_storage_bucket)

    # Create and install container
    container = Container(ocr=ocr, embedder=embedder, storage=storage)
    container.install()

    # Store in app state for route access
    app.state.supabase = supabase
    app.state.container = container

    # Initialize DBOS
    DBOS.launch()

    yield

    # Cleanup
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

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(entries.router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
