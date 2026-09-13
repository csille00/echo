"""Route registration."""

from fastapi import FastAPI

from journal_search.api.routes import entries, health, search


def register_routes(app: FastAPI) -> None:
    """Mount all API routers."""
    app.include_router(health.router)
    app.include_router(entries.router, prefix="/api/v1")
    app.include_router(search.router, prefix="/api/v1")
