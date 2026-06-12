from app.core.documents import source_label
from app.core.prompts import RAG_SYSTEM_PROMPT
from app.core.logger import logger
from app.core.supabase import supabase_configured
from app.llm.base import BaseLLMProvider
from app.rag.mappers import estimate_tokens
from app.rag.schemas import ChatMessage
from app.rag.tool_loop import run_tool_augmented_generation
from app.tools.registry import tool_registry


class ResponseGenerator:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.client = llm_provider

    async def generate(
        self,
        query: str,
        context_chunks: list[dict],
        summary: str = "",
        recent_messages: list[ChatMessage] | None = None,
    ) -> dict:
        """
        Genera una respuesta basada ÚNICAMENTE en los chunks recuperados.
        Retorna la respuesta y metadatos para evaluación.
        """
        if not context_chunks:
            logger.warning("No hay contexto disponible para generar respuesta")
            return {
                "answer": "No encontré información suficiente en los documentos para responder esta pregunta.",
                "context_used": [],
                "context_text": "",
            }

        context_text = self._build_context(context_chunks)
        conversation_context = self._build_conversation_context(summary, recent_messages or [])
        prompt = RAG_SYSTEM_PROMPT.format(
            context=self._merge_context(context_text, conversation_context),
            question=query,
        )

        logger.info(f"Generando respuesta | contexto: {len(context_text)} chars | pregunta: '{query}'")

        tools_used = []
        tokens_input = estimate_tokens(prompt + conversation_context)
        tokens_output = 0

        if supabase_configured() and tool_registry.list_tool_names():
            logger.info("Generando respuesta con herramientas Supabase")
            tool_result = await run_tool_augmented_generation(
                llm_provider=self.client,
                query=query,
                context_text=self._merge_context(context_text, conversation_context),
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
            "context_used": context_chunks,
            "context_text": context_text,
            "tools_used": tools_used,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
        }

    def _build_conversation_context(
        self,
        summary: str,
        recent_messages: list[ChatMessage],
    ) -> str:
        parts: list[str] = []
        if summary.strip():
            parts.append(f"Resumen de conversación: {summary.strip()}")
        for message in recent_messages:
            parts.append(f"{message.role}: {message.content}")
        return "\n".join(parts)

    def _merge_context(self, context_text: str, conversation_context: str) -> str:
        if not conversation_context:
            return context_text
        return f"{conversation_context}\n\n---\n\n{context_text}"

    def _build_context(self, chunks: list[dict]) -> str:
        """
        Construye el bloque de contexto que va dentro del prompt.
        Cada chunk se numera y se indica su fuente.
        """
        context_parts = []
        for index, chunk in enumerate(chunks, 1):
            text = chunk["text"]
            context_parts.append(f"[Fragmento {index} - Fuente: {source_label(chunk)}]\n{text}")

        return "\n\n---\n\n".join(context_parts)
