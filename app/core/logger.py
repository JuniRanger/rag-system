import sys
from loguru import logger
from app.core.config import settings

def setup_logger():
    # Eliminar logger por defecto 
    logger.remove()
    
    # Logger para la terminal — lo que ves mientras corre el sistema
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <white>{message}</white>",
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=True
    )
    
    # Logger para archivo — historial permanente en disco
    logger.add(
        "logs/rag_system.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{line} - {message}",
        level="INFO",
        rotation="10 MB",    # Crea un archivo nuevo cuando llega a 10MB
        retention="7 days",  # Borra logs más viejos de 7 días
        compression="zip"    # Comprime los logs viejos
    )
    
    return logger

# Esta linea garantiza que el logger se inicialice desde cualquier archivo
logger = setup_logger() 