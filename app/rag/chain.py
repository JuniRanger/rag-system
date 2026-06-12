from app.retrieval.search import VectorSearch
from app.retrieval.reranker import Reranker
from app.llm.generator import ResponseGenerator
from app.core.logger import logger
from app.embeddings.base import BaseEmbeddingProvider
from app.llm.base import BaseLLMProvider
from app.rag.mappers import build_function_calls, build_source_references, estimate_tokens
from app.rag.schemas import RAGRequest
from app.vectorstore.base import BaseVectorStoreProvider


class RAGChain:
    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        vector_store_provider: BaseVectorStoreProvider,
        llm_provider: BaseLLMProvider,
        use_reranker: bool = True,
    ):
        self.searcher = VectorSearch(
            embedding_provider=embedding_provider,
            vector_store_provider=vector_store_provider,
        )
        self.reranker = Reranker(llm_provider=llm_provider)
        self.generator = ResponseGenerator(llm_provider=llm_provider)
        self.default_use_reranker = use_reranker

    async def run(self, request: RAGRequest) -> dict:
        """
        Ejecuta el flujo RAG completo:
        pregunta → búsqueda → reranking → generación → respuesta
        """
        query = request.effective_query()
        options = request.options
        use_reranker = (
            options.use_reranker
            if options.use_reranker is not None
            else self.default_use_reranker
        )

        logger.info(f"=== RAG Chain iniciada | query: '{query}' ===")

        chunks = await self.searcher.search_with_threshold(
            query=query,
            threshold=0.4,
            top_k=options.top_k,
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
                "tools_used": [],
                "function_calls": [],
                "tokens_input": estimate_tokens(query),
                "tokens_output": 0,
            }

        chunks_retrieved = len(chunks)
        logger.info(f"Chunks recuperados: {chunks_retrieved}")

        if use_reranker:
            chunks = await self.reranker.rerank(query, chunks)

        chunks = chunks[: options.max_chunks]
        chunks_used = len(chunks)
        logger.info(f"Chunks usados tras reranking: {chunks_used}")

        result = await self.generator.generate(
            query=query,
            context_chunks=chunks,
            summary=request.summary,
            recent_messages=request.recent_messages,
        )

        function_calls = build_function_calls(result.get("tools_used", []))
        sources = build_source_references(chunks)

        response = {
            "query": query,
            "answer": result["answer"],
            "sources": sources,
            "chunks_retrieved": chunks_retrieved,
            "chunks_used": chunks_used,
            "context_used": result["context_used"],
            "tools_used": result.get("tools_used", []),
            "function_calls": function_calls,
            "tokens_input": result.get("tokens_input", 0),
            "tokens_output": result.get("tokens_output", 0),
        }

        logger.info(f"=== RAG Chain completada | fuentes: {len(sources)} ===")
        return response
