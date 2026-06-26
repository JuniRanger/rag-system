import asyncio
import time
from collections.abc import AsyncIterator

from app.rag.chain import RAGChain
from app.rag.context_plan import GenerationPlan
from app.rag.context_plan import plan_request
from app.rag.exceptions import StreamingNotSupportedError
from app.rag.mappers import build_function_calls, build_source_references, error_response, estimate_tokens
from app.rag.memory import ConversationSummarizer, should_refresh_summary
from app.rag.schemas import RAGRequest, RAGResponse, RAGResponseMetadata
from app.rag.sse import format_sse_event
from app.core.logger import logger
from app.embeddings.base import BaseEmbeddingProvider
from app.llm.base import BaseLLMProvider
from app.llm.generator import uses_tool_augmented_generation
from app.vectorstore.base import BaseVectorStoreProvider


def _compute_stream_metrics(
    started_at: float,
    first_token_at: float | None,
    finished_at: float,
    tokens_output: int,
) -> tuple[int, int, float]:
    latency_ms = int((finished_at - started_at) * 1000)
    ttft_ms = int((first_token_at - started_at) * 1000) if first_token_at else latency_ms

    if first_token_at and finished_at > first_token_at and tokens_output > 0:
        generation_seconds = finished_at - first_token_at
        tokens_per_second = round(tokens_output / generation_seconds, 2)
    else:
        tokens_per_second = 0.0

    return ttft_ms, latency_ms, tokens_per_second


def _build_metadata(
    plan: GenerationPlan,
    result: dict,
    latency_ms: int,
    ttft_ms: int = 0,
    tokens_per_second: float = 0.0,
) -> RAGResponseMetadata:
    function_calls = result.get("function_calls") or build_function_calls(result.get("tools_used", []))
    return RAGResponseMetadata(
        latency_ms=latency_ms,
        ttft_ms=ttft_ms,
        tokens_per_second=tokens_per_second,
        intent=plan.intent.value,
        vehicle_changed=plan.vehicle_changed,
        rag_executed=plan.run_rag,
        retrieved_chunks=result.get("chunks_retrieved", 0),
        used_chunks=result.get("chunks_used", 0),
        tokens_input=result.get("tokens_input", 0),
        tokens_output=result.get("tokens_output", 0),
        tools_used=function_calls,
        function_calls=function_calls,
        context_used=result.get("context_used", []),
    )


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
        self.summarizer = ConversationSummarizer(llm_provider=llm_provider)
        logger.info("RAG Pipeline inicializado")

    async def run(self, request: RAGRequest) -> RAGResponse:
        """Punto de entrada principal del sistema RAG con DTOs tipados."""
        conversation_id = request.resolved_conversation_id()
        started_at = time.perf_counter()

        if request.message.role != "user":
            return error_response(
                conversation_id,
                "El mensaje actual debe tener role='user'.",
                summary=request.summary,
                working_memory=request.working_memory,
            )

        query = request.effective_query()
        if not query:
            return error_response(
                conversation_id,
                "El mensaje no puede estar vacío.",
                summary=request.summary,
                working_memory=request.working_memory,
            )

        try:
            plan = plan_request(request)
            result = await self.chain.run(request, plan)
            summary = await self._resolve_summary(request, result["answer"])
            latency_ms = int((time.perf_counter() - started_at) * 1000)

            return RAGResponse(
                success=True,
                conversation_id=conversation_id,
                answer=result["answer"],
                summary=summary,
                working_memory=plan.working_memory,
                sources=result["sources"],
                metadata=_build_metadata(plan, result, latency_ms),
            )
        except Exception as error:
            logger.error(f"Error en RAG Pipeline: {error}")
            response = error_response(
                conversation_id,
                f"Error interno del sistema: {error}",
                summary=request.summary,
                working_memory=request.working_memory,
            )
            response.metadata.latency_ms = int((time.perf_counter() - started_at) * 1000)
            return response

    async def run_stream(self, request: RAGRequest) -> AsyncIterator[str]:
        """Genera eventos SSE (token, done) para respuestas en streaming."""
        conversation_id = request.resolved_conversation_id()
        started_at = time.perf_counter()

        if request.message.role != "user":
            yield format_sse_event(
                "done",
                error_response(
                    conversation_id,
                    "El mensaje actual debe tener role='user'.",
                    summary=request.summary,
                    working_memory=request.working_memory,
                ).model_dump(),
            )
            return

        query = request.effective_query()
        if not query:
            yield format_sse_event(
                "done",
                error_response(
                    conversation_id,
                    "El mensaje no puede estar vacío.",
                    summary=request.summary,
                    working_memory=request.working_memory,
                ).model_dump(),
            )
            return

        if uses_tool_augmented_generation():
            yield format_sse_event(
                "done",
                error_response(
                    conversation_id,
                    "El streaming no está disponible cuando hay herramientas Supabase activas. "
                    "Usa POST /query en su lugar.",
                    summary=request.summary,
                    working_memory=request.working_memory,
                ).model_dump(),
            )
            return

        try:
            plan = plan_request(request)
            if plan.run_rag:
                context = await self.chain.retrieve_context(request, plan)
            else:
                context = self.chain._skipped_rag_context(plan)

            answer_parts: list[str] = []
            first_token_at: float | None = None

            async for token in self.chain.stream_generation(plan, context):
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                answer_parts.append(token)
                yield format_sse_event("token", {"content": token})

            finished_at = time.perf_counter()
            answer = "".join(answer_parts)
            summary = await self._resolve_summary(request, answer)
            tokens_output = estimate_tokens(answer)
            ttft_ms, latency_ms, tokens_per_second = _compute_stream_metrics(
                started_at,
                first_token_at,
                finished_at,
                tokens_output,
            )

            sources = build_source_references(context["chunks"]) if plan.run_rag else []
            stream_result = {
                "chunks_retrieved": context["chunks_retrieved"],
                "chunks_used": context["chunks_used"],
                "context_used": context["chunks"] if plan.run_rag else [],
                "tokens_input": estimate_tokens(query),
                "tokens_output": tokens_output,
            }

            yield format_sse_event(
                "done",
                RAGResponse(
                    success=True,
                    conversation_id=conversation_id,
                    answer=answer,
                    summary=summary,
                    working_memory=plan.working_memory,
                    sources=sources,
                    metadata=_build_metadata(
                        plan,
                        stream_result,
                        latency_ms,
                        ttft_ms=ttft_ms,
                        tokens_per_second=tokens_per_second,
                    ),
                ).model_dump(),
            )
        except StreamingNotSupportedError as error:
            yield format_sse_event(
                "done",
                error_response(
                    conversation_id,
                    str(error),
                    summary=request.summary,
                    working_memory=request.working_memory,
                ).model_dump(),
            )
        except Exception as error:
            logger.error(f"Error en RAG Pipeline (stream): {error}")
            response = error_response(
                conversation_id,
                f"Error interno del sistema: {error}",
                summary=request.summary,
                working_memory=request.working_memory,
            )
            response.metadata.latency_ms = int((time.perf_counter() - started_at) * 1000)
            yield format_sse_event("done", response.model_dump())

    async def _resolve_summary(self, request: RAGRequest, answer: str) -> str:
        if not should_refresh_summary(request):
            return request.summary

        return await self.summarizer.summarize(
            previous_summary=request.summary,
            recent_messages=request.recent_messages,
            user_message=request.message.content,
            assistant_answer=answer,
        )

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