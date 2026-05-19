from app.llm.client import OllamaClient
from app.core.prompts import RAG_SYSTEM_PROMPT
from app.core.logger import logger

class ResponseGenerator:
    def __init__(self):
        self.client = OllamaClient()

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

        # Paso 3: Llamar al LLM
        messages = [{"role": "user", "content": prompt}]
        answer = self.client.chat(messages)

        logger.info(f"Respuesta generada: {len(answer)} caracteres")

        return {
            "answer": answer,
            "context_used": context_chunks,
            "context_text": context_text
        }

    def _build_context(self, chunks: list[dict]) -> str:
        """
        Construye el bloque de contexto que va dentro del prompt.
        Cada chunk se numera y se indica su fuente.
        """
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("filename", "desconocido")
            text = chunk["text"]
            context_parts.append(f"[Fragmento {i} - Fuente: {source}]\n{text}")

        return "\n\n---\n\n".join(context_parts)