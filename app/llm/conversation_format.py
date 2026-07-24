"""Formateo de contexto conversacional para el Prompt Builder (no el Planner)."""

from __future__ import annotations

from app.rag.schemas import ChatMessage

_ROLE_LABELS = {
    "user": "Usuario",
    "assistant": "Asistente",
    "system": "Sistema",
    "tool": "Herramienta",
}


def format_conversation_context(
    summary: str,
    recent_messages: list[ChatMessage],
) -> str:
    """
    Convierte summary + recent_messages estructurados en texto para el LLM.

    Omite secciones vacías. No inventa placeholders si no hay datos.
    """
    sections: list[str] = []

    summary_text = (summary or "").strip()
    if summary_text:
        sections.append(
            "================================================================================\n"
            "RESUMEN DE LA CONVERSACIÓN\n"
            "================================================================================\n\n"
            f"{summary_text}"
        )

    if recent_messages:
        lines: list[str] = []
        for message in recent_messages:
            content = (message.content or "").strip()
            if not content:
                continue
            label = _ROLE_LABELS.get(message.role, message.role.capitalize())
            lines.append(f"{label}: {content}")
        if lines:
            sections.append(
                "================================================================================\n"
                "MENSAJES RECIENTES\n"
                "================================================================================\n\n"
                + "\n\n".join(lines)
            )

    return "\n\n".join(sections)
