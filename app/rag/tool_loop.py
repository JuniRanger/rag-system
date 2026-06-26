import asyncio
import json
from typing import Any

from app.core.logger import logger
from app.core.prompts import TOOL_AUGMENTED_RAG_PROMPT
from app.llm.base import BaseLLMProvider
from app.rag.mappers import estimate_tokens
from app.tools.executor import tool_executor
from app.tools.registry import tool_registry

MAX_TOOL_ROUNDS = 4


def _parse_tool_arguments(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        return json.loads(raw)
    return {}


async def run_tool_augmented_generation(
    llm_provider: BaseLLMProvider,
    query: str,
    context_text: str,
    conversation_history: str = "",
    working_memory: str = "",
) -> dict:
    """
    Ejecuta generación con tool calling de Ollama.
    Combina contexto RAG con consultas estructuradas a Supabase.
    """
    tools = tool_registry.get_ollama_schemas()
    if not tools:
        raise ValueError("No hay herramientas registradas para tool calling.")

    history_text = conversation_history.strip() or "(sin historial previo)"
    memory_text = working_memory.strip() or "(sin contexto activo de diagnóstico)"
    prompt = TOOL_AUGMENTED_RAG_PROMPT.format(
        working_memory=memory_text,
        conversation_history=history_text,
        context=context_text,
        question=query,
    )
    messages: list[dict] = [{"role": "user", "content": prompt}]
    tools_used: list[dict] = []
    tokens_input = estimate_tokens(prompt)
    tokens_output = 0

    answer = ""
    message: dict = {}
    for round_index in range(MAX_TOOL_ROUNDS):
        message = await llm_provider.chat_with_tools_async(messages=messages, tools=tools)
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            answer = (message.get("content") or "").strip()
            tokens_output += estimate_tokens(answer)
            break

        messages.append(message)
        logger.info(f"Tool round {round_index + 1}: {len(tool_calls)} llamada(s)")

        for tool_call in tool_calls:
            function = tool_call.get("function") or {}
            tool_name = function.get("name", "")
            arguments = _parse_tool_arguments(function.get("arguments"))
            result = await asyncio.to_thread(tool_executor.execute, tool_name, arguments)
            tools_used.append(
                {
                    "tool": tool_name,
                    "arguments": arguments,
                    "status": result.get("status"),
                    "output": result.get("output"),
                }
            )
            tokens_input += estimate_tokens(json.dumps(arguments, ensure_ascii=False))
            tokens_output += estimate_tokens(str(result.get("output", "")))
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
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
    }
