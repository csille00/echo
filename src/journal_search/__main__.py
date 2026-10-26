"""Main entry point for running the application."""

import uvicorn

from journal_search.api import create_app
from journal_search.config import get_settings


def main() -> None:
    settings = get_settings()
    app = create_app(settings)

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.listen_port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
