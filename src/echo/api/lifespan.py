"""FastAPI lifespan hooks."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dbos import DBOS
from fastapi import FastAPI

from echo.api.bootstrap import build_container
from echo.config import get_settings
from echo.db.migrate import apply_migrations
from echo.db.session import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown for the API process."""
    settings = get_settings()
    init_db(settings)
    await apply_migrations()

    container = await build_container(settings)
    container.install()
    app.state.container = container

    DBOS.launch()

    yield

    await container.close()
    await close_db()
    DBOS.destroy()
