import sys
from loguru import logger
from app.core.config import settings

def setup_logger():
    # Eliminar logger por defecto
    logger.remove()

    # Único handler: stdout (terminal y docker logs)
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <white>{message}</white>",
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=True,
    )

    return logger

# Inicializa el logger al importar el módulo
logger = setup_logger()
