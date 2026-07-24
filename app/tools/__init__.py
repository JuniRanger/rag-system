from app.core.config import settings
from app.core.logger import logger
from app.core.supabase import supabase_configured
from app.tools.registry import tool_registry


def register_all_tools() -> None:
    """Registra herramientas disponibles según la configuración activa."""
    if not settings.ENABLE_RAG_TOOLS:
        logger.info(
            "ENABLE_RAG_TOOLS=false — webhook/sync activos, tool calling RAG deshabilitado"
        )
        return

    if supabase_configured():
        from app.tools.implementations.supabase.read_tools import register_read_tools

        register_read_tools()
    else:
        logger.info("Supabase no configurado — herramientas de BD omitidas")

    from app.tools.implementations.citas import register_cita_tools

    register_cita_tools()
    logger.info(f"Herramientas registradas: {tool_registry.list_tool_names()}")
