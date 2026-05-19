from app.vectorstore.qdrant_client import get_qdrant_manager
from app.embeddings.model import get_embedder
from app.core.logger import logger

class VectorIndexer:
    def __init__(self):
        self.qdrant = get_qdrant_manager()
        self.embedder = get_embedder()

    def index_chunks(self, chunks: list[dict], recreate: bool = False):
        """
        Pipeline completo de indexación:
        chunks de texto → embeddings → Qdrant
        """
        logger.info(f"Iniciando indexación de {len(chunks)} chunks")

        # Paso 1: Crear colección en Qdrant
        self.qdrant.create_collection(recreate=recreate)

        # Paso 2: Generar embeddings para todos los chunks
        logger.info("Generando embeddings...")
        chunks_with_embeddings = self.embedder.embed_chunks(chunks)

        # Paso 3: Insertar en Qdrant
        logger.info("Insertando en Qdrant...")
        self.qdrant.insert_points(chunks_with_embeddings)

        # Paso 4: Verificar que todo quedó bien
        info = self.qdrant.get_collection_info()
        logger.info(f"Indexación completa — Colección: {info}")

        return info

    def get_index_stats(self) -> dict:
        """Retorna estadísticas del índice actual."""
        return self.qdrant.get_collection_info()