from app.vectorstore.qdrant_client import get_qdrant_manager
from app.embeddings.model import get_embedder
from app.core.config import settings
from app.core.logger import logger

class VectorSearch:
    def __init__(self):
        self.qdrant = get_qdrant_manager()
        self.embedder = get_embedder()

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """
        Convierte la pregunta en vector y busca los chunks más similares.
        Este es el corazón del sistema RAG.
        """
        k = top_k or settings.TOP_K
        logger.info(f"Buscando: '{query}' | top_k={k}")

        # Paso 1: Convertir pregunta a vector
        query_vector = self.embedder.embed_text(query)

        # Paso 2: Buscar en Qdrant
        results = self.qdrant.search(query_vector, top_k=k)

        logger.info(f"Encontrados {len(results)} fragmentos relevantes")
        for i, r in enumerate(results):
            logger.debug(f"  [{i+1}] score={r['score']:.4f} | {r['filename']} | chunk {r['chunk_index']}")

        return results

    def search_with_threshold(self, query: str, threshold: float = 0.5) -> list[dict]:
        """
        Igual que search() pero filtra resultados con score menor al umbral.
        Evita pasar contexto irrelevante al LLM cuando nada es suficientemente similar.
        """
        results = self.search(query, top_k=settings.TOP_K)
        filtered = [r for r in results if r["score"] >= threshold]

        if not filtered:
            logger.warning(f"Ningún resultado superó el umbral de {threshold}")
        else:
            logger.info(f"Resultados tras filtro de umbral: {len(filtered)}/{len(results)}")

        return filtered