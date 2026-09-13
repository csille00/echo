"""FastAPI lifespan hooks."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from dbos import DBOS
from fastapi import FastAPI

from journal_search.api.bootstrap import build_container
from journal_search.config import get_settings
from journal_search.db.session import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown for the API process."""
    settings = get_settings()
    init_db(settings)

    container = await build_container(settings)
    container.install()
    app.state.container = container

    DBOS.launch()

    yield

    await container.close()
    await close_db()
    DBOS.destroy()
