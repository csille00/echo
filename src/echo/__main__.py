"""Main entry point for running the application."""

import uvicorn

from echo.config import get_settings


def main() -> None:
    settings = get_settings()

    uvicorn.run(
        "echo.api:create_app",
        factory=True,
        host=settings.api_host,
        port=settings.listen_port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
