from collections.abc import AsyncIterator

from app.core.config import settings
from app.core.documents import source_label
from app.core.prompts import (
    CONVERSATION_PROMPT,
    MEMORY_REQUEST_PROMPT,
    OUT_OF_SCOPE_PROMPT,
    RAG_SYSTEM_PROMPT,
    SCHEDULING_FALLBACK_PROMPT,
    SUPABASE_RAG_PROMPT,
)
from app.core.logger import logger
from app.core.supabase import supabase_configured
from app.llm.base import BaseLLMProvider
from app.rag.context_plan import GenerationPlan
from app.rag.decision_tree import (
    GenerationDecision,
    GenerationPath,
    resolve_generation_path,
)
from app.rag.mappers import estimate_tokens
from app.rag.tool_loop import run_tool_augmented_generation, stream_tool_augmented_generation
from app.tools.registry import tool_registry

NO_CONTEXT_ANSWER = (
    "No encontré información suficiente en los documentos para responder esta pregunta."
)
NO_CONVERSATION_HISTORY = "(no proporcionado)"
NO_RAG_CONTEXT = "(no aplica — consulta sin búsqueda documental)"

# Respuesta unificada para solicitudes bloqueadas (sin LLM)
REJECTION_ANSWER = (
    "Como tu asistente mecánico, estoy especializado únicamente en resolver dudas sobre autos, "
    "motos y fallas mecánicas. ¿Hay algo en lo que pueda ayudarte con tu vehículo?"
)


def uses_tool_augmented_generation() -> bool:
    return settings.ENABLE_RAG_TOOLS and bool(tool_registry.list_tool_names())


class ResponseGenerator:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.client = llm_provider

    def _decide(self, plan: GenerationPlan):
        return resolve_generation_path(plan, tools_available=uses_tool_augmented_generation())

    async def generate(
        self,
        plan: GenerationPlan,
        context_chunks: list[dict],
        fallback_context: str | None = None,
    ) -> dict:
        decision = self._decide(plan)

        if decision.path == GenerationPath.REJECTION:
            logger.info(
                "Árbol de decisión → REJECTION | Solicitud fuera de ámbito (sin LLM)."
            )
            return {
                "answer": REJECTION_ANSWER,
                "context_used": [],
                "context_text": "",
                "tools_used": [],
                "tokens_input": 0,
                "tokens_output": 0,
            }

        prompt, context_text, history_text = self._build_prompt(
            plan=plan,
            decision=decision,
            context_chunks=context_chunks,
            fallback_context=fallback_context,
        )

        logger.info(
            f"Árbol de decisión → {decision.path.value} | prompt={decision.prompt_family} | "
            f"intent={plan.intent.value} | contexto: {len(context_text)} chars | "
            f"historial: {len(history_text)} chars | pregunta: '{plan.current_question}'"
        )

        tools_used = []
        tokens_input = estimate_tokens(prompt)

        if decision.use_tools:
            logger.info(
                f"Generando con herramientas | role={plan.user_role} | "
                f"tool_mode={decision.tool_mode} | tools={tool_registry.list_tool_names()}"
            )
            tool_result = await run_tool_augmented_generation(
                llm_provider=self.client,
                query=plan.current_question,
                context_text=context_text,
                conversation_history=history_text,
                working_memory=plan.working_memory.to_prompt_text(),
                user_role=plan.user_role,
                tool_mode=decision.tool_mode,
                user_profile=plan.user_profile_text,
                cita_usuario=plan.cita_usuario,
            )
            answer = tool_result["answer"]
            tools_used = tool_result.get("tools_used", [])
            tokens_input += tool_result.get("tokens_input", 0)
            tokens_output = tool_result.get("tokens_output", 0)
        else:
            if plan.use_tools and not uses_tool_augmented_generation():
                logger.warning(
                    "Plan pedía tools pero no están disponibles "
                    f"(ENABLE_RAG_TOOLS={settings.ENABLE_RAG_TOOLS} | "
                    f"registradas={tool_registry.list_tool_names()}). "
                    f"Usando path={decision.path.value}."
                )
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
    ) -> AsyncIterator[str | dict]:
        """
        Emite tokens (str). Si hay tools, también puede emitir un dict final
        ``{"_meta": {...}}`` con tools_used y tokens.
        """
        decision = self._decide(plan)

        if decision.path == GenerationPath.REJECTION:
            logger.info("Árbol de decisión → REJECTION (stream) | token estático.")
            yield REJECTION_ANSWER
            return

        prompt, context_text, history_text = self._build_prompt(
            plan=plan,
            decision=decision,
            context_chunks=context_chunks,
            fallback_context=fallback_context,
        )

        if decision.use_tools:
            logger.info(
                f"Árbol de decisión → {decision.path.value} (stream+tools) | "
                f"role={plan.user_role} | tool_mode={decision.tool_mode}"
            )
            async for item in stream_tool_augmented_generation(
                llm_provider=self.client,
                query=plan.current_question,
                context_text=context_text,
                conversation_history=history_text,
                working_memory=plan.working_memory.to_prompt_text(),
                user_role=plan.user_role,
                tool_mode=decision.tool_mode,
                user_profile=plan.user_profile_text,
                cita_usuario=plan.cita_usuario,
            ):
                yield item
            return

        if plan.use_tools and not uses_tool_augmented_generation():
            logger.warning(
                "Plan pedía tools pero no están disponibles. "
                f"Usando path={decision.path.value} en streaming."
            )

        logger.info(
            f"Árbol de decisión → {decision.path.value} (stream) | "
            f"intent={plan.intent.value} | pregunta: '{plan.current_question}'"
        )
        messages = [{"role": "user", "content": prompt}]
        async for token in self.client.stream_response_async(messages):
            yield token

    def _build_prompt(
        self,
        plan: GenerationPlan,
        decision: GenerationDecision,
        context_chunks: list[dict],
        fallback_context: str | None = None,
    ) -> tuple[str, str, str]:
        """Selecciona el prompt según GenerationPath (lo que consume el modelo)."""
        history_text = plan.conversation_history.strip() or NO_CONVERSATION_HISTORY
        working_memory_text = plan.working_memory.to_prompt_text()

        if decision.path == GenerationPath.CONVERSATION:
            prompt = CONVERSATION_PROMPT.format(question=plan.current_question)
            return prompt, NO_RAG_CONTEXT, ""

        if decision.path == GenerationPath.MEMORY:
            prompt = MEMORY_REQUEST_PROMPT.format(
                conversation_history=history_text,
                question=plan.current_question,
            )
            return prompt, NO_RAG_CONTEXT, history_text

        if decision.path == GenerationPath.REJECTION:
            # Defensa: no debería llegar aquí (se intercepta antes).
            prompt = OUT_OF_SCOPE_PROMPT.format(question=plan.current_question)
            return prompt, NO_RAG_CONTEXT, ""

        if decision.path == GenerationPath.SCHEDULING_FALLBACK:
            prompt = SCHEDULING_FALLBACK_PROMPT.format(
                working_memory=working_memory_text,
                conversation_history=history_text,
                question=plan.current_question,
            )
            return prompt, NO_RAG_CONTEXT, history_text

        # SCHEDULING_TOOLS / AUTOMOTIVE_TOOLS / AUTOMOTIVE_RAG
        # El tool loop reconstruye TOOL_AUGMENTED; aquí armamos contexto + prompt RAG
        # (también sirve para estimar tokens_input antes del loop).
        context_text = self._build_context(context_chunks, fallback_context)
        if decision.path in {
            GenerationPath.SCHEDULING_TOOLS,
            GenerationPath.AUTOMOTIVE_TOOLS,
        }:
            # Contexto se inyecta en tool_loop; devolvemos texto para el loop.
            return "", context_text, history_text

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
