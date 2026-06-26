from collections.abc import AsyncIterator

from app.core.config import settings
from app.core.documents import source_label
from app.core.prompts import (
    CONVERSATION_PROMPT,
    MEMORY_REQUEST_PROMPT,
    OUT_OF_SCOPE_PROMPT,
    RAG_SYSTEM_PROMPT,
    SUPABASE_RAG_PROMPT,
)
from app.core.logger import logger
from app.core.supabase import supabase_configured
from app.llm.base import BaseLLMProvider
from app.rag.context_plan import GenerationPlan
from app.rag.exceptions import StreamingNotSupportedError
from app.rag.intent import QueryIntent
from app.rag.mappers import estimate_tokens
from app.rag.tool_loop import run_tool_augmented_generation
from app.tools.registry import tool_registry

NO_CONTEXT_ANSWER = (
    "No encontré información suficiente en los documentos para responder esta pregunta."
)
NO_CONVERSATION_HISTORY = "(no proporcionado)"
NO_RAG_CONTEXT = "(no aplica — consulta sin búsqueda documental)"


def uses_tool_augmented_generation() -> bool:
    return (
        settings.ENABLE_RAG_TOOLS
        and supabase_configured()
        and bool(tool_registry.list_tool_names())
    )


class ResponseGenerator:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.client = llm_provider

    async def generate(
        self,
        plan: GenerationPlan,
        context_chunks: list[dict],
        fallback_context: str | None = None,
    ) -> dict:
        prompt, context_text, history_text = self._build_prompt(
            plan=plan,
            context_chunks=context_chunks,
            fallback_context=fallback_context,
        )

        logger.info(
            f"Generando respuesta | intent={plan.intent.value} | contexto: {len(context_text)} chars | "
            f"historial: {len(history_text)} chars | pregunta: '{plan.current_question}'"
        )

        tools_used = []
        tokens_input = estimate_tokens(prompt)
        tokens_output = 0

        if plan.run_rag and uses_tool_augmented_generation():
            logger.info("Generando respuesta con herramientas Supabase")
            tool_result = await run_tool_augmented_generation(
                llm_provider=self.client,
                query=plan.current_question,
                context_text=context_text,
                conversation_history=history_text,
                working_memory=plan.working_memory.to_prompt_text(),
            )
            answer = tool_result["answer"]
            tools_used = tool_result.get("tools_used", [])
            tokens_input += tool_result.get("tokens_input", 0)
            tokens_output += tool_result.get("tokens_output", 0)
        else:
            messages = [{"role": "user", "content": prompt}]
            answer = await self.client.generate_response_async(messages)
            tokens_output = estimate_tokens(answer)

        logger.info(f"Respuesta generada: {len(answer)} caracteres")

        return {
            "answer": answer,
            "context_used": context_chunks if plan.run_rag else [],
            "context_text": context_text,
            "tools_used": tools_used,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
        }

    async def stream_generate(
        self,
        plan: GenerationPlan,
        context_chunks: list[dict],
        fallback_context: str | None = None,
    ) -> AsyncIterator[str]:
        if plan.run_rag and uses_tool_augmented_generation():
            raise StreamingNotSupportedError(
                "El streaming no está disponible cuando hay herramientas Supabase activas. "
                "Usa POST /query en su lugar."
            )

        prompt, _, _ = self._build_prompt(
            plan=plan,
            context_chunks=context_chunks,
            fallback_context=fallback_context,
        )

        logger.info(
            f"Generando respuesta en streaming | intent={plan.intent.value} | "
            f"pregunta: '{plan.current_question}'"
        )
        messages = [{"role": "user", "content": prompt}]
        async for token in self.client.stream_response_async(messages):
            yield token

    def _build_prompt(
        self,
        plan: GenerationPlan,
        context_chunks: list[dict],
        fallback_context: str | None = None,
    ) -> tuple[str, str, str]:
        history_text = plan.conversation_history.strip() or NO_CONVERSATION_HISTORY
        working_memory_text = plan.working_memory.to_prompt_text()

        if plan.intent == QueryIntent.CONVERSATION:
            prompt = CONVERSATION_PROMPT.format(question=plan.current_question)
            return prompt, NO_RAG_CONTEXT, ""

        if plan.intent == QueryIntent.MEMORY_REQUEST:
            prompt = MEMORY_REQUEST_PROMPT.format(
                conversation_history=history_text,
                question=plan.current_question,
            )
            return prompt, NO_RAG_CONTEXT, history_text

        if plan.intent == QueryIntent.OUT_OF_SCOPE:
            prompt = OUT_OF_SCOPE_PROMPT.format(question=plan.current_question)
            return prompt, NO_RAG_CONTEXT, ""

        context_text = self._build_context(context_chunks, fallback_context)
        template = SUPABASE_RAG_PROMPT if supabase_configured() else RAG_SYSTEM_PROMPT
        prompt = template.format(
            working_memory=working_memory_text,
            conversation_history=history_text,
            context=context_text,
            question=plan.current_question,
        )
        return prompt, context_text, history_text

    def _build_context(
        self,
        chunks: list[dict],
        fallback_context: str | None = None,
    ) -> str:
        if not chunks:
            return fallback_context or NO_CONTEXT_ANSWER

        context_parts = []
        for index, chunk in enumerate(chunks, 1):
            text = chunk["text"]
            metadata = chunk.get("metadata", {})
            header_parts = [f"Fragmento {index}"]
            record_id = metadata.get("record_id")
            if record_id is not None:
                header_parts.append(f"ID registro: {record_id}")
            header_parts.append(f"Fuente: {source_label(chunk)}")
            context_parts.append(f"[{' | '.join(header_parts)}]\n{text}")

        return "\n\n---\n\n".join(context_parts)
