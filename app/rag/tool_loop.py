import json
from typing import Any

from app.core.logger import logger
from app.core.prompts import TOOL_AUGMENTED_RAG_PROMPT
from app.llm.base import BaseLLMProvider
from app.tools.executor import tool_executor
from app.tools.registry import tool_registry

MAX_TOOL_ROUNDS = 4


def _parse_tool_arguments(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        return json.loads(raw)
    return {}


def run_tool_augmented_generation(
    llm_provider: BaseLLMProvider,
    query: str,
    context_text: str,
) -> dict:
    """
    Ejecuta generación con tool calling de Ollama.
    Combina contexto RAG con consultas estructuradas a Supabase.
    """
    tools = tool_registry.get_ollama_schemas()
    if not tools:
        raise ValueError("No hay herramientas registradas para tool calling.")

    prompt = TOOL_AUGMENTED_RAG_PROMPT.format(context=context_text, question=query)
    messages: list[dict] = [{"role": "user", "content": prompt}]
    tools_used: list[dict] = []

    answer = ""
    for round_index in range(MAX_TOOL_ROUNDS):
        message = llm_provider.chat_with_tools(messages=messages, tools=tools)
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            answer = (message.get("content") or "").strip()
            break

        messages.append(message)
        logger.info(f"Tool round {round_index + 1}: {len(tool_calls)} llamada(s)")

        for tool_call in tool_calls:
            function = tool_call.get("function") or {}
            tool_name = function.get("name", "")
            arguments = _parse_tool_arguments(function.get("arguments"))
            result = tool_executor.execute(tool_name, arguments)
            tools_used.append(
                {
                    "tool": tool_name,
                    "arguments": arguments,
                    "status": result.get("status"),
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )
    else:
        answer = (message.get("content") or "").strip()
        if not answer:
            answer = "No pude completar la consulta con las herramientas disponibles."

    return {
        "answer": answer,
        "tools_used": tools_used,
    }
