from app.core.chunks import prepare_chunks_for_indexing
from app.core.logger import logger
from app.core.providers import get_embedding_provider, get_vector_store_provider
from app.embeddings.base import BaseEmbeddingProvider
from app.vectorstore.base import BaseVectorStoreProvider


class VectorIndexer:
    """
    Orquesta la vectorización de chunks ya fragmentados.
    Responsabilidad: chunks normalizados → embeddings → vectorstore.
    """

    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider | None = None,
        vector_store_provider: BaseVectorStoreProvider | None = None,
    ):
        self.vector_store = vector_store_provider or get_vector_store_provider()
        self.embedder = embedding_provider or get_embedding_provider()

    def index_chunks(self, chunks: list[dict], recreate: bool = False) -> dict:
        """
        Pipeline de indexación:
        chunks de ingesta → embeddings → almacén vectorial
        """
        if not chunks:
            raise ValueError("No hay chunks para indexar.")

        logger.info(f"Iniciando indexación de {len(chunks)} chunks")
        prepared_chunks = prepare_chunks_for_indexing(chunks)
        vector_size = self.embedder.embedding_dimension

        try:
            self.vector_store.create_collection(recreate=recreate, vector_size=vector_size)
            logger.info(f"Generando embeddings con dimensión={vector_size}...")
            chunks_with_embeddings = self.embedder.embed_chunks(prepared_chunks)
            logger.info("Insertando puntos en el almacén vectorial...")
            inserted = self.vector_store.insert_points(chunks_with_embeddings)
            info = self.vector_store.get_collection_info()
        except Exception as exc:
            logger.error(f"Error durante la indexación: {exc}")
            raise

        logger.info(
            f"Indexación completa — puntos insertados={inserted} | colección={info}"
        )
        return info

    def get_index_stats(self) -> dict:
        """Retorna estadísticas del índice actual."""
        return self.vector_store.get_collection_info()
