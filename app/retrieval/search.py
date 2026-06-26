from app.core.config import settings
from app.core.documents import source_label
from app.core.logger import logger
from app.embeddings.base import BaseEmbeddingProvider
from app.vectorstore.base import BaseVectorStoreProvider


class VectorSearch:
    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        vector_store_provider: BaseVectorStoreProvider,
    ):
        self.vector_store = vector_store_provider
        self.embedder = embedding_provider

    async def search(self, query: str, top_k: int | None = None) -> list[dict]:
        """
        Convierte la pregunta en vector y busca los chunks más similares.
        Este es el corazón del sistema RAG.
        """
        k = top_k or settings.TOP_K
        logger.info(f"Buscando: '{query}' | top_k={k}")

        query_vector = await self.embedder.embed_text_async(query)
        results = await self.vector_store.search_async(query_vector, top_k=k)

        logger.info(f"Encontrados {len(results)} fragmentos relevantes")
        for i, result in enumerate(results):
            metadata = result.get("metadata", {})
            chunk_index = metadata.get("chunk_index", 0)
            logger.debug(
                f"  [{i+1}] score={result['score']:.4f} | {source_label(result)} | chunk {chunk_index}"
            )

        return results

    async def search_with_threshold(
        self,
        query: str,
        threshold: float = 0.5,
        top_k: int | None = None,
    ) -> list[dict]:
        """
        Igual que search() pero filtra resultados con score menor al umbral.
        Evita pasar contexto irrelevante al LLM cuando nada es suficientemente similar.
        """
        results = await self.search(query, top_k=top_k or settings.TOP_K)
        filtered = [result for result in results if result["score"] >= threshold]

        if not filtered:
            logger.warning(f"Ningún resultado superó el umbral de {threshold}")
        else:
            logger.info(f"Resultados tras filtro de umbral: {len(filtered)}/{len(results)}")

        return filtered
