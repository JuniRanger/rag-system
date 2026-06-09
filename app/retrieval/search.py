from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.vectorstore.qdrant_client import get_qdrant_manager
from app.embeddings.model import get_embedder
from app.core.config import settings
from app.core.logger import logger

class VectorSearch:
    def __init__(self):
        self.qdrant = get_qdrant_manager()
        self.embedder = get_embedder()

    def _build_filter(self) -> Filter | None:
        table = (settings.RAG_SEARCH_SUPABASE_TABLE or "").strip()
        if not table:
            return None
        return Filter(
            must=[
                FieldCondition(
                    key="supabase_table",
                    match=MatchValue(value=table),
                )
            ]
        )

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """
        Convierte la pregunta en vector y busca los chunks más similares.
        """
        k = top_k or settings.TOP_K
        payload_filter = self._build_filter()
        logger.info(
            f"Buscando: '{query}' | top_k={k} | "
            f"filtro supabase_table={settings.RAG_SEARCH_SUPABASE_TABLE or 'ninguno'}"
        )

        query_vector = self.embedder.embed_text(query)
        results = self.qdrant.search(
            query_vector,
            top_k=k,
            payload_filter=payload_filter,
        )

        logger.info(f"Encontrados {len(results)} fragmentos relevantes")
        for i, r in enumerate(results):
            logger.debug(
                f"  [{i+1}] score={r['score']:.4f} | {r['filename']} | "
                f"table={r.get('supabase_table', '')} | chunk {r['chunk_index']}"
            )

        return results

    def search_with_threshold(self, query: str, threshold: float = 0.5) -> list[dict]:
        """
        Igual que search() pero filtra resultados con score menor al umbral.
        Evita pasar contexto irrelevante al LLM cuando nada es suficientemente similar.
        """
        results = self.search(query, top_k=settings.TOP_K)
        filtered = [r for r in results if r["score"] >= threshold]

        if not filtered:
            logger.warning(
                f"Ningún resultado superó el umbral de {threshold}. "
                f"Top scores: {[round(r['score'], 4) for r in results[:5]]}"
            )
        else:
            logger.info(f"Resultados tras filtro de umbral: {len(filtered)}/{len(results)}")

        return filtered