"""Route registration."""

from fastapi import FastAPI

from journal_search.api.routes import auth, entries, health, oidc, search


def register_routes(app: FastAPI) -> None:
    """Mount all API routers."""
    app.include_router(health.router)
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(oidc.router, prefix="/api/v1")
    app.include_router(entries.router, prefix="/api/v1")
    app.include_router(search.router, prefix="/api/v1")
