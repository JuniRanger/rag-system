from functools import lru_cache
from typing import TYPE_CHECKING, Any

from app.core.config import settings
from app.core.logger import logger

if TYPE_CHECKING:
    from supabase import Client


def supabase_configured() -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY and settings.SUPABASE_TABLE)


def require_supabase_config():
    missing = []
    if not settings.SUPABASE_URL:
        missing.append("SUPABASE_URL")
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if not settings.SUPABASE_TABLE:
        missing.append("SUPABASE_TABLE")
    if not settings.SUPABASE_TEXT_COLUMNS.strip():
        missing.append("SUPABASE_TEXT_COLUMNS")

    if missing:
        raise ValueError(f"Faltan variables de entorno de Supabase: {', '.join(missing)}")


@lru_cache()
def get_supabase_client() -> "Client | Any":
    require_supabase_config()

    from supabase import create_client

    logger.info("Inicializando cliente de Supabase")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
