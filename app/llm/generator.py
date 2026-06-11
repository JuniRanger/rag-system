from app.core.documents import source_label
from app.core.prompts import RAG_SYSTEM_PROMPT
from app.core.logger import logger
from app.core.supabase import supabase_configured
from app.llm.base import BaseLLMProvider
from app.rag.tool_loop import run_tool_augmented_generation
from app.tools.registry import tool_registry

class ResponseGenerator:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.client = llm_provider

    def generate(self, query: str, context_chunks: list[dict]) -> dict:
        """
        Genera una respuesta basada ÚNICAMENTE en los chunks recuperados.
        Retorna la respuesta y metadatos para evaluación.
        """
        if not context_chunks:
            logger.warning("No hay contexto disponible para generar respuesta")
            return {
                "answer": "No encontré información suficiente en los documentos para responder esta pregunta.",
                "context_used": [],
                "context_text": ""
            }

        # Paso 1: Construir el contexto concatenando los chunks
        context_text = self._build_context(context_chunks)

        # Paso 2: Formatear el prompt con contexto y pregunta
        prompt = RAG_SYSTEM_PROMPT.format(
            context=context_text,
            question=query
        )

        logger.info(f"Generando respuesta | contexto: {len(context_text)} chars | pregunta: '{query}'")

        # Paso 3: Llamar al LLM (con herramientas Supabase si están disponibles)
        tools_used = []
        if supabase_configured() and tool_registry.list_tool_names():
            logger.info("Generando respuesta con herramientas Supabase")
            tool_result = run_tool_augmented_generation(
                llm_provider=self.client,
                query=query,
                context_text=context_text,
            )
            answer = tool_result["answer"]
            tools_used = tool_result.get("tools_used", [])
        else:
            messages = [{"role": "user", "content": prompt}]
            answer = self.client.generate_response(messages)

        logger.info(f"Respuesta generada: {len(answer)} caracteres")

        return {
            "answer": answer,
            "context_used": context_chunks,
            "context_text": context_text,
            "tools_used": tools_used,
        }

    def _build_context(self, chunks: list[dict]) -> str:
        """
        Construye el bloque de contexto que va dentro del prompt.
        Cada chunk se numera y se indica su fuente.
        """
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            text = chunk["text"]
            context_parts.append(f"[Fragmento {i} - Fuente: {source_label(chunk)}]\n{text}")

        return "\n\n---\n\n".join(context_parts)
