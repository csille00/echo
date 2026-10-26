"""Apply packaged SQL migrations on startup."""

import logging
from pathlib import Path

from sqlalchemy import text

from echo.db.session import get_engine
from echo.db.sql_split import split_sql

logger = logging.getLogger(__name__)


def migrations_dir() -> Path:
    """Directory of *.sql files shipped with the package."""
    packaged = Path(__file__).resolve().parent.parent / "migrations"
    if packaged.is_dir():
        return packaged
    cwd = Path("migrations")
    if cwd.is_dir():
        return cwd
    raise FileNotFoundError(f"No migrations directory at {packaged} or {cwd.resolve()}")


async def apply_migrations() -> None:
    """Run any *.sql files that are not yet recorded in schema_migrations."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
            """)
        )

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT filename FROM schema_migrations"))
        applied = {row[0] for row in result}

    for path in sorted(migrations_dir().glob("*.sql")):
        if path.name in applied:
            continue
        statements = split_sql(path.read_text(encoding="utf-8"))
        async with engine.begin() as conn:
            for statement in statements:
                await conn.execute(text(statement))
            await conn.execute(
                text("INSERT INTO schema_migrations (filename) VALUES (:filename)"),
                {"filename": path.name},
            )
        logger.info("Applied migration %s", path.name)
