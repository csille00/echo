"""Serve the built web UI from the API process."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse


def register_spa(app: FastAPI, web_root: str) -> None:
    """Serve static files and fall back to index.html for client-side routes."""
    root = Path(web_root).resolve()
    index = root / "index.html"
    if not root.is_dir() or not index.is_file():
        raise RuntimeError(f"WEB_ROOT must be a directory containing index.html: {root}")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        if full_path:
            candidate = (root / full_path).resolve()
            if candidate.is_relative_to(root) and candidate.is_file():
                return FileResponse(candidate)
        return FileResponse(index)
