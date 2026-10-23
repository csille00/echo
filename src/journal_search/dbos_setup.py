"""DBOS initialization helpers (self-hosted — no DBOS Cloud required)."""

from dbos import DBOS
from dbos._dbos_config import DBOSConfig

from journal_search.config import Settings


def build_dbos_config(settings: Settings) -> DBOSConfig:
    """Build a DBOS config from application settings."""
    config: DBOSConfig = {
        "name": "journal_search",
        "database_url": settings.dbos_database_url,
        "runtimeConfig": {"start": ["journal_search.workflows"]},
    }

    if settings.dbos_conductor_url:
        config["conductor_url"] = settings.dbos_conductor_url
    if settings.dbos_conductor_key is not None:
        config["conductor_key"] = settings.dbos_conductor_key.get_secret_value()

    return config


def init_dbos(settings: Settings) -> DBOS:
    """Initialize the DBOS singleton (call DBOS.launch() from app lifespan)."""
    return DBOS(config=build_dbos_config(settings))
