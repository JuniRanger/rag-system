import asyncio
import json
from collections.abc import AsyncIterator
from datetime import date
from typing import Any, Literal

from app.core.logger import logger
from app.llm.prompts import (
    ROLE_RULES_ADMIN,
    ROLE_RULES_CLIENT,
    TOOL_AUGMENTED_RAG_PROMPT,
    TOOL_FINAL_USER_NUDGE,
    TOOL_MODE_RULES_ALL,
    TOOL_MODE_RULES_NONE,
    TOOL_MODE_RULES_SCHEDULING,
)
from app.llm.base import BaseLLMProvider
from app.rag.mappers import estimate_tokens
from app.tools.executor import tool_executor
from app.tools.registry import tool_registry

MAX_TOOL_ROUNDS = 4
ADMIN_BLOCKED_TOOLS = frozenset({"crearCitaAPI"})
SCHEDULING_TOOLS = frozenset({"crearCitaAPI"})
STREAM_CHUNK_SIZE = 24

ADMIN_SCHEDULING_DENIED = (
    "Como administrador no puedes agendar citas desde este asistente. "
    "Las citas las agenda el cliente; yo puedo ayudarte con diagnósticos y consultas técnicas."
)


def _parse_tool_arguments(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        return json.loads(raw)
    return {}


def _role_rules(user_role: str) -> str:
    if user_role == "admin":
        return ROLE_RULES_ADMIN.strip()
    return ROLE_RULES_CLIENT.strip()


def _tool_mode_rules(tool_mode: str) -> str:
    if tool_mode == "scheduling":
        return TOOL_MODE_RULES_SCHEDULING.strip()
    if tool_mode == "all":
        return TOOL_MODE_RULES_ALL.strip()
    return TOOL_MODE_RULES_NONE.strip()


def _tools_for_mode(user_role: str, tool_mode: str) -> list[dict]:
    schemas = tool_registry.get_ollama_schemas()

    if tool_mode == "scheduling":
        schemas = [
            schema
            for schema in schemas
            if schema.get("function", {}).get("name") in SCHEDULING_TOOLS
        ]
    elif tool_mode == "none":
        return []

    if user_role == "admin":
        schemas = [
            schema
            for schema in schemas
            if schema.get("function", {}).get("name") not in ADMIN_BLOCKED_TOOLS
        ]

    return schemas


def _chunk_text(text: str, size: int = STREAM_CHUNK_SIZE) -> list[str]:
    if not text:
        return []
    return [text[i : i + size] for i in range(0, len(text), size)]


def _build_tool_prompt(
    *,
    query: str,
    context_text: str,
    conversation_context: str,
    working_memory: str,
    user_role: str,
    tool_mode: str,
    user_profile: str = "(sin datos de usuario en el request)",
) -> tuple[str, str]:
    today_date = date.today().isoformat()
    conversation_text = (conversation_context or "").strip()
    memory_text = working_memory.strip() or "(sin contexto activo de diagnóstico)"
    profile_text = user_profile.strip() or "(sin datos de usuario en el request)"
    effective_context = (
        "(sin contexto documental — modo agendamiento de cita)"
        if tool_mode == "scheduling"
        else context_text
    )
    prompt = TOOL_AUGMENTED_RAG_PROMPT.format(
        today_date=today_date,
        user_role=user_role,
        role_rules=_role_rules(user_role),
        user_profile=profile_text,
        tool_mode=tool_mode,
        tool_mode_rules=_tool_mode_rules(tool_mode),
        working_memory=memory_text,
        conversation_context=conversation_text,
        context=effective_context,
        question=query,
    )
    return prompt, effective_context


def _inject_cita_usuario(
    arguments: dict,
    cita_usuario: dict[str, str] | None,
) -> dict:
    """Adjunta usuario del request. El LLM no debe enviarlo ni inventarlo."""
    cleaned = {
        "fecha": str(arguments.get("fecha") or "").strip(),
        "vehiculo": str(arguments.get("vehiculo") or "").strip(),
        "producto": str(arguments.get("producto") or "").strip(),
    }
    if cita_usuario:
        cleaned["usuario"] = {
            "id": str(cita_usuario.get("id") or "").strip(),
            "nombre": str(cita_usuario.get("nombre") or "").strip(),
            "correo": str(cita_usuario.get("correo") or "").strip(),
        }
    return cleaned


def _strip_tool_json_leak(text: str) -> str:
    """Si el modelo filtró JSON/tool syntax al usuario, no lo dejes pasar como respuesta."""
    stripped = (text or "").strip()
    if not stripped:
        return stripped
    lower = stripped.lower()
    looks_like_dump = (
        (stripped.startswith("{") and stripped.endswith("}"))
        or (stripped.startswith("[") and stripped.endswith("]"))
        or "tool_calls" in lower
        or '"function"' in lower
        or lower.startswith("function call")
        or lower.startswith("crearCitaAPI".lower() + "(")
    )
    if looks_like_dump:
        return (
            "Listo, procesé tu solicitud. Si necesitas algo más sobre la cita "
            "o el diagnóstico, dímelo."
        )
    return text


async def _execute_tool_rounds(
    llm_provider: BaseLLMProvider,
    *,
    messages: list[dict],
    tools: list[dict],
    user_role: str,
    cita_usuario: dict[str, str] | None = None,
) -> dict:
    """Ejecuta rondas de function calling. Retorna estado listo para respuesta final."""
    tools_used: list[dict] = []
    tokens_input = 0
    tokens_output = 0
    answer = ""
    message: dict = {}
    needs_final_stream = False

    for round_index in range(MAX_TOOL_ROUNDS):
        message = await llm_provider.chat_with_tools_async(messages=messages, tools=tools)
        tool_calls = message.get("tool_calls") or []

        if not tool_calls:
            answer = (message.get("content") or "").strip()
            tokens_output += estimate_tokens(answer)
            logger.info(
                f"Tool loop sin function_calls en ronda {round_index + 1} | "
                f"respuesta directa ({len(answer)} chars)"
            )
            break

        messages.append(message)
        logger.info(f"Tool round {round_index + 1}: {len(tool_calls)} llamada(s)")

        for tool_call in tool_calls:
            function = tool_call.get("function") or {}
            tool_name = function.get("name", "")
            arguments = _parse_tool_arguments(function.get("arguments"))
            if tool_name == "crearCitaAPI":
                arguments = _inject_cita_usuario(arguments, cita_usuario)
            logger.info(f"Function call solicitada: {tool_name} | args={arguments}")

            if user_role == "admin" and tool_name in ADMIN_BLOCKED_TOOLS:
                result = {
                    "status": "error",
                    "tool": tool_name,
                    "output": (
                        "Acción denegada: los administradores no pueden agendar citas "
                        "ni usar crearCitaAPI."
                    ),
                }
            else:
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

        # Tras tools hace falta otra pasada LLM para la respuesta final
        needs_final_stream = True
    else:
        needs_final_stream = True
        answer = (message.get("content") or "").strip()

    if needs_final_stream and not answer:
        messages.append(
            {
                "role": "user",
                "content": TOOL_FINAL_USER_NUDGE,
            }
        )

    return {
        "messages": messages,
        "tools_used": tools_used,
        "answer": _strip_tool_json_leak(answer),
        "tokens_input": tokens_input,
        "tokens_output": tokens_output,
        "needs_final_stream": bool(needs_final_stream and not answer),
    }


async def run_tool_augmented_generation(
    llm_provider: BaseLLMProvider,
    query: str,
    context_text: str,
    conversation_context: str = "",
    working_memory: str = "",
    user_role: Literal["admin", "client"] | str = "client",
    tool_mode: str = "all",
    user_profile: str = "(sin datos de usuario en el request)",
    cita_usuario: dict[str, str] | None = None,
) -> dict:
    """Ejecuta generación con tool calling (respuesta completa)."""
    tools = _tools_for_mode(user_role, tool_mode)
    if not tools:
        if user_role == "admin" and tool_mode == "scheduling":
            logger.info("Admin en modo scheduling — cita denegada sin tools")
            return {
                "answer": ADMIN_SCHEDULING_DENIED,
                "tools_used": [],
                "tokens_input": 0,
                "tokens_output": estimate_tokens(ADMIN_SCHEDULING_DENIED),
            }
        raise ValueError(
            f"No hay herramientas disponibles | role={user_role} | tool_mode={tool_mode} | "
            f"registradas={tool_registry.list_tool_names()}"
        )

    logger.info(
        f"Tool loop iniciado | role={user_role} | tool_mode={tool_mode} | "
        f"tools={[t.get('function', {}).get('name') for t in tools]}"
    )

    prompt, _ = _build_tool_prompt(
        query=query,
        context_text=context_text,
        conversation_context=conversation_context,
        working_memory=working_memory,
        user_role=user_role,
        tool_mode=tool_mode,
        user_profile=user_profile,
    )
    messages: list[dict] = [{"role": "user", "content": prompt}]
    tokens_input = estimate_tokens(prompt)

    state = await _execute_tool_rounds(
        llm_provider,
        messages=messages,
        tools=tools,
        user_role=user_role,
        cita_usuario=cita_usuario,
    )

    answer = state["answer"]
    tokens_output = state["tokens_output"]

    if state["needs_final_stream"] or not answer:
        answer = await llm_provider.generate_response_async(state["messages"])
        tokens_output += estimate_tokens(answer)

    answer = _strip_tool_json_leak(answer or "")
    if not answer:
        answer = "No pude completar la consulta con las herramientas disponibles."

    return {
        "answer": answer,
        "tools_used": state["tools_used"],
        "tokens_input": tokens_input + state["tokens_input"],
        "tokens_output": tokens_output,
    }


async def stream_tool_augmented_generation(
    llm_provider: BaseLLMProvider,
    query: str,
    context_text: str,
    conversation_context: str = "",
    working_memory: str = "",
    user_role: Literal["admin", "client"] | str = "client",
    tool_mode: str = "all",
    user_profile: str = "(sin datos de usuario en el request)",
    cita_usuario: dict[str, str] | None = None,
) -> AsyncIterator[str | dict]:
    """
    Tools activas + streaming:
    1) Rondas de function calling (sin stream; Ollama necesita el mensaje completo).
    2) Stream de la respuesta final al usuario.

    Yields:
      - str: tokens de la respuesta final
      - dict con clave "_meta": metadata (tools_used, tokens_*) al terminar
    """
    tools = _tools_for_mode(user_role, tool_mode)
    if not tools:
        if user_role == "admin" and tool_mode == "scheduling":
            logger.info("Admin en modo scheduling — cita denegada sin tools")
            for chunk in _chunk_text(ADMIN_SCHEDULING_DENIED):
                yield chunk
            yield {
                "_meta": {
                    "answer": ADMIN_SCHEDULING_DENIED,
                    "tools_used": [],
                    "tokens_input": 0,
                    "tokens_output": estimate_tokens(ADMIN_SCHEDULING_DENIED),
                }
            }
            return
        raise ValueError(
            f"No hay herramientas disponibles | role={user_role} | tool_mode={tool_mode} | "
            f"registradas={tool_registry.list_tool_names()}"
        )

    logger.info(
        f"Tool loop+stream iniciado | role={user_role} | tool_mode={tool_mode} | "
        f"tools={[t.get('function', {}).get('name') for t in tools]}"
    )

    prompt, _ = _build_tool_prompt(
        query=query,
        context_text=context_text,
        conversation_context=conversation_context,
        working_memory=working_memory,
        user_role=user_role,
        tool_mode=tool_mode,
        user_profile=user_profile,
    )
    messages: list[dict] = [{"role": "user", "content": prompt}]
    tokens_input = estimate_tokens(prompt)

    state = await _execute_tool_rounds(
        llm_provider,
        messages=messages,
        tools=tools,
        user_role=user_role,
        cita_usuario=cita_usuario,
    )

    answer_parts: list[str] = []
    tokens_output = state["tokens_output"]

    if state["answer"] and not state["needs_final_stream"]:
        final_answer = _strip_tool_json_leak(state["answer"])
    else:
        streamed: list[str] = []
        async for token in llm_provider.stream_response_async(state["messages"]):
            if token:
                streamed.append(token)
        final_answer = _strip_tool_json_leak("".join(streamed).strip())

    if not final_answer:
        final_answer = "No pude completar la consulta con las herramientas disponibles."

    for chunk in _chunk_text(final_answer):
        answer_parts.append(chunk)
        yield chunk

    tokens_output = tokens_output or estimate_tokens(final_answer)

    yield {
        "_meta": {
            "answer": final_answer,
            "tools_used": state["tools_used"],
            "tokens_input": tokens_input + state["tokens_input"],
            "tokens_output": tokens_output,
        }
    }
