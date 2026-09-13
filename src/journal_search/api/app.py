"""FastAPI application factory."""

from fastapi import FastAPI

from journal_search.api.lifespan import lifespan
from journal_search.api.middleware import configure_middleware
from journal_search.api.router import register_routes
from journal_search.config import Settings, get_settings
from journal_search.dbos_setup import init_dbos


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

    init_dbos(settings, fastapi=app)
    configure_middleware(app, settings)
    register_routes(app)

    return app
