from collections.abc import AsyncIterator

from app.retrieval.search import VectorSearch
from app.retrieval.reranker import Reranker
from app.llm.generator import ResponseGenerator
from app.core.logger import logger
from app.embeddings.base import BaseEmbeddingProvider
from app.llm.base import BaseLLMProvider
from app.rag.context_plan import GenerationPlan
from app.rag.mappers import build_function_calls, build_source_references
from app.rag.schemas import RAGRequest
from app.vectorstore.base import BaseVectorStoreProvider

EMPTY_VECTOR_CONTEXT = (
    "No hay documentos cargados en el sistema para esta consulta específica."
)


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

    async def run(self, request: RAGRequest, plan: GenerationPlan) -> dict:
        """Ejecuta el flujo según el plan: RAG condicional + generación."""
        if plan.run_rag:
            context = await self.retrieve_context(request, plan)
        else:
            context = self._skipped_rag_context(plan)

        result = await self.generator.generate(
            plan=plan,
            context_chunks=context["chunks"],
            fallback_context=context["context_str"],
        )

        function_calls = build_function_calls(result.get("tools_used", []))
        sources = build_source_references(context["chunks"])

        response = {
            "query": plan.current_question,
            "answer": result["answer"],
            "sources": sources,
            "chunks_retrieved": context["chunks_retrieved"],
            "chunks_used": context["chunks_used"],
            "context_used": result["context_used"],
            "tools_used": result.get("tools_used", []),
            "function_calls": function_calls,
            "tokens_input": result.get("tokens_input", 0),
            "tokens_output": result.get("tokens_output", 0),
        }

        logger.info(
            f"=== RAG Chain completada | intent={plan.intent.value} | "
            f"fuentes: {len(sources)} ==="
        )
        return response

    async def stream_generation(
        self,
        plan: GenerationPlan,
        context: dict,
    ) -> AsyncIterator[str]:
        async for token in self.generator.stream_generate(
            plan=plan,
            context_chunks=context["chunks"],
            fallback_context=context["context_str"],
        ):
            yield token

    async def retrieve_context(self, request: RAGRequest, plan: GenerationPlan) -> dict:
        options = request.options
        use_reranker = (
            options.use_reranker
            if options.use_reranker is not None
            else self.default_use_reranker
        )

        logger.info(
            f"Ejecutando RAG | pregunta: '{plan.current_question}' | "
            f"retrieval_query: {len(plan.retrieval_query)} chars"
        )

        chunks = await self.searcher.search_with_threshold(
            query=plan.retrieval_query,
            threshold=0.4,
            top_k=options.top_k,
        )

        if not chunks:
            logger.warning(
                "Sin resultados relevantes en la base de datos — "
                "continuando con contexto vacío hacia el LLM"
            )
            return {
                "query": plan.current_question,
                "chunks": [],
                "context_str": EMPTY_VECTOR_CONTEXT,
                "chunks_retrieved": 0,
                "chunks_used": 0,
            }

        chunks_retrieved = len(chunks)
        logger.info(f"Chunks recuperados: {chunks_retrieved}")

        if use_reranker:
            chunks = await self.reranker.rerank(plan.retrieval_query, chunks)

        chunks = chunks[: options.max_chunks]
        chunks_used = len(chunks)
        logger.info(f"Chunks usados tras reranking: {chunks_used}")

        return {
            "query": plan.current_question,
            "chunks": chunks,
            "context_str": None,
            "chunks_retrieved": chunks_retrieved,
            "chunks_used": chunks_used,
        }

    @staticmethod
    def _skipped_rag_context(plan: GenerationPlan) -> dict:
        logger.info(f"RAG omitido | intent={plan.intent.value}")
        return {
            "query": plan.current_question,
            "chunks": [],
            "context_str": None,
            "chunks_retrieved": 0,
            "chunks_used": 0,
        }
