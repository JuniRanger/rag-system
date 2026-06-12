import asyncio
import time

from app.rag.chain import RAGChain
from app.rag.mappers import build_function_calls, error_response
from app.rag.schemas import RAGRequest, RAGResponse, RAGResponseMetadata
from app.core.logger import logger
from app.embeddings.base import BaseEmbeddingProvider
from app.llm.base import BaseLLMProvider
from app.vectorstore.base import BaseVectorStoreProvider


class RAGPipeline:
    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        vector_store_provider: BaseVectorStoreProvider,
        llm_provider: BaseLLMProvider,
        use_reranker: bool = True,
    ):
        self.chain = RAGChain(
            embedding_provider=embedding_provider,
            vector_store_provider=vector_store_provider,
            llm_provider=llm_provider,
            use_reranker=use_reranker,
        )
        logger.info("RAG Pipeline inicializado")

    async def run(self, request: RAGRequest) -> RAGResponse:
        """Punto de entrada principal del sistema RAG con DTOs tipados."""
        conversation_id = request.resolved_conversation_id()
        started_at = time.perf_counter()

        if request.message.role != "user":
            return error_response(conversation_id, "El mensaje actual debe tener role='user'.")

        query = request.effective_query()
        if not query:
            return error_response(conversation_id, "El mensaje no puede estar vacío.")

        try:
            result = await self.chain.run(request)
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            function_calls = result.get("function_calls") or build_function_calls(
                result.get("tools_used", [])
            )

            return RAGResponse(
                success=True,
                conversation_id=conversation_id,
                answer=result["answer"],
                sources=result["sources"],
                metadata=RAGResponseMetadata(
                    latency_ms=latency_ms,
                    retrieved_chunks=result["chunks_retrieved"],
                    used_chunks=result["chunks_used"],
                    tokens_input=result.get("tokens_input", 0),
                    tokens_output=result.get("tokens_output", 0),
                    tools_used=function_calls,
                    function_calls=function_calls,
                    context_used=result.get("context_used", []),
                ),
            )
        except Exception as error:
            logger.error(f"Error en RAG Pipeline: {error}")
            response = error_response(conversation_id, f"Error interno del sistema: {error}")
            response.metadata.latency_ms = int((time.perf_counter() - started_at) * 1000)
            return response

    def query(self, question: str, use_reranker: bool | None = None) -> dict:
        """
        Atajo síncrono compatible con scripts y evaluación.
        Convierte una pregunta simple al DTO y retorna un dict legacy.
        """
        from app.rag.schemas import ChatMessage, RAGQueryOptions

        options = RAGQueryOptions()
        if use_reranker is not None:
            options.use_reranker = use_reranker

        request = RAGRequest(
            message=ChatMessage(role="user", content=question),
            options=options,
        )
        response = asyncio.run(self.run(request))
        payload = response.model_dump()

        payload["query"] = question
        payload["context_used"] = response.metadata.context_used
        payload["metadata"]["chunks_retrieved"] = response.metadata.retrieved_chunks
        payload["metadata"]["chunks_used"] = response.metadata.used_chunks
        return payload
