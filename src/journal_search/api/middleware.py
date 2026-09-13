"""HTTP middleware configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from journal_search.config import Settings


def configure_middleware(app: FastAPI, settings: Settings) -> None:
    """Register application middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
