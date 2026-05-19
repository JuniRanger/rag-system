from functools import lru_cache
from app.embeddings.embedder import Embedder
from app.core.logger import logger

@lru_cache()
def get_embedder() -> Embedder:
    """
    Retorna siempre la misma instancia del Embedder.
    lru_cache garantiza que el modelo no se carga dos veces.
    """
    logger.info("Inicializando instancia única del Embedder")
    return Embedder()