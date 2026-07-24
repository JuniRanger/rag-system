"""Árbol de decisión: intent → camino de generación que consume el modelo.

Fuente de verdad documentada en context/intents.md y context/flows.md.
El router heurístico (`detect_intent` + `plan_request`) clasifica el mensaje;
este módulo traduce el plan a un `GenerationPath` explícito para el generator.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from app.rag.intent import REJECT_OUT_OF_SCOPE_REQUEST, QueryIntent

if TYPE_CHECKING:
    from app.rag.context_plan import GenerationPlan


class GenerationPath(str, Enum):
    """Camino efectivo de generación (lo que el modelo / sistema consume)."""

    CONVERSATION = "conversation"  # CONVERSATION_PROMPT
    MEMORY = "memory"  # MEMORY_REQUEST_PROMPT
    REJECTION = "rejection"  # REJECTION_ANSWER (sin LLM)
    SCHEDULING_TOOLS = "scheduling_tools"  # TOOL_AUGMENTED + tool_mode=scheduling
    SCHEDULING_FALLBACK = "scheduling_fallback"  # prosa sin tools
    AUTOMOTIVE_TOOLS = "automotive_tools"  # TOOL_AUGMENTED + tool_mode=all
    AUTOMOTIVE_RAG = "automotive_rag"  # RAG_SYSTEM / SUPABASE_RAG


@dataclass(frozen=True)
class GenerationDecision:
    """Resultado del árbol: qué prompt / loop debe ejecutarse."""

    path: GenerationPath
    call_llm: bool
    use_tools: bool
    tool_mode: str
    prompt_family: str


def resolve_generation_path(
    plan: GenerationPlan,
    *,
    tools_available: bool,
) -> GenerationDecision:
    """
    Árbol de decisión post-plan (lo que consume el modelo).

    Orden alineado con flows.md:
      conversation → CONVERSATION_PROMPT
      memory_request → MEMORY_REQUEST_PROMPT
      out_of_scope / sentinel → REJECTION_ANSWER (sin LLM)
      scheduling + tools ON → tool loop (scheduling)
      scheduling + tools OFF → SCHEDULING_FALLBACK_PROMPT
      automotive + tools ON → tool loop (all) + contexto RAG
      automotive + tools OFF → RAG_SYSTEM / SUPABASE_RAG
    """
    if (
        plan.intent == QueryIntent.OUT_OF_SCOPE
        or plan.current_question == REJECT_OUT_OF_SCOPE_REQUEST
    ):
        return GenerationDecision(
            path=GenerationPath.REJECTION,
            call_llm=False,
            use_tools=False,
            tool_mode="none",
            prompt_family="REJECTION_ANSWER",
        )

    if plan.intent == QueryIntent.CONVERSATION:
        return GenerationDecision(
            path=GenerationPath.CONVERSATION,
            call_llm=True,
            use_tools=False,
            tool_mode="none",
            prompt_family="CONVERSATION_PROMPT",
        )

    if plan.intent == QueryIntent.MEMORY_REQUEST:
        return GenerationDecision(
            path=GenerationPath.MEMORY,
            call_llm=True,
            use_tools=False,
            tool_mode="none",
            prompt_family="MEMORY_REQUEST_PROMPT",
        )

    if plan.intent == QueryIntent.SCHEDULING:
        if plan.use_tools and tools_available:
            return GenerationDecision(
                path=GenerationPath.SCHEDULING_TOOLS,
                call_llm=True,
                use_tools=True,
                tool_mode="scheduling",
                prompt_family="TOOL_AUGMENTED_RAG_PROMPT",
            )
        return GenerationDecision(
            path=GenerationPath.SCHEDULING_FALLBACK,
            call_llm=True,
            use_tools=False,
            tool_mode="none",
            prompt_family="SCHEDULING_FALLBACK_PROMPT",
        )

    # AUTOMOTIVE (y cualquier caída residual con run_rag)
    if plan.use_tools and tools_available:
        return GenerationDecision(
            path=GenerationPath.AUTOMOTIVE_TOOLS,
            call_llm=True,
            use_tools=True,
            tool_mode=plan.tool_mode or "all",
            prompt_family="TOOL_AUGMENTED_RAG_PROMPT",
        )

    return GenerationDecision(
        path=GenerationPath.AUTOMOTIVE_RAG,
        call_llm=True,
        use_tools=False,
        tool_mode="none",
        prompt_family="RAG_SYSTEM_PROMPT|SUPABASE_RAG_PROMPT",
    )
