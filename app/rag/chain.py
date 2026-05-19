from app.retrieval.search import VectorSearch
from app.retrieval.reranker import Reranker
from app.llm.generator import ResponseGenerator
from app.core.config import settings
from app.core.logger import logger

class RAGChain:
    def __init__(self, use_reranker: bool = True):
        self.searcher = VectorSearch()
        self.reranker = Reranker() if use_reranker else None
        self.generator = ResponseGenerator()
        self.use_reranker = use_reranker

    def run(self, query: str) -> dict:
        """
        Ejecuta el flujo RAG completo:
        pregunta → búsqueda → reranking → generación → respuesta
        """
        logger.info(f"=== RAG Chain iniciada | query: '{query}' ===")

        # Paso 1: Recuperar chunks relevantes con umbral
        chunks = self.searcher.search_with_threshold(
            query=query,
            threshold=0.4
        )

        if not chunks:
            logger.warning("Sin resultados relevantes en la base de datos")
            return {
                "query": query,
                "answer": "No encontré información suficiente en los documentos para responder esta pregunta.",
                "sources": [],
                "chunks_retrieved": 0,
                "chunks_used": 0,
                "context_used": [],
            }

        chunks_retrieved = len(chunks)
        logger.info(f"Chunks recuperados: {chunks_retrieved}")

        # Paso 2: Reranking (opcional pero recomendado)
        if self.use_reranker:
            chunks = self.reranker.rerank(query, chunks)
            # Usar solo los top 3 tras reranking para no sobrecargar el contexto
            chunks = chunks[:3]

        chunks_used = len(chunks)
        logger.info(f"Chunks usados tras reranking: {chunks_used}")

        # Paso 3: Generar respuesta
        result = self.generator.generate(query, chunks)

        # Paso 4: Construir respuesta final con metadatos
        sources = list(set([c.get("filename", "") for c in chunks]))

        response = {
            "query": query,
            "answer": result["answer"],
            "sources": sources,
            "chunks_retrieved": chunks_retrieved,
            "chunks_used": chunks_used,
            "context_used": result["context_used"]
        }

        logger.info(f"=== RAG Chain completada | fuentes: {sources} ===")
        return response