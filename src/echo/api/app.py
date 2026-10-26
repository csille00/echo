"""FastAPI application factory."""

from fastapi import FastAPI

from echo.api.lifespan import lifespan
from echo.api.middleware import configure_middleware
from echo.api.router import register_routes
from echo.api.static import register_spa
from echo.config import Settings, get_settings
from echo.dbos_setup import init_dbos


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI application."""
    if settings is None:
        settings = get_settings()

    app = FastAPI(
        title="Echo",
        description="AI-powered journal OCR and search",
        version="0.1.0",
        lifespan=lifespan,
    )

    init_dbos(settings)
    configure_middleware(app, settings)
    register_routes(app)
    if settings.web_root:
        register_spa(app, settings.web_root)

    return app
