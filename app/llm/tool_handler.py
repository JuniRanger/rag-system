import json
from typing import Any

from app.llm.client import OllamaClient
from app.tools.tools_registry import TOOLS
from app.core.logger import logger


def _parse_tool_arguments(raw: Any) -> dict:
    """Ollama puede devolver arguments como dict o como string JSON."""
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return {}
        return json.loads(raw)
    raise TypeError(f"arguments inesperado: {type(raw)}")


class ToolHandler:
    """Orquesta function calling con Ollama y ejecución local de TOOLS."""

    def __init__(self):
        self.client = OllamaClient()

    def execute(self, messages: list[dict]) -> str:
        response = self.client.chat_with_tools(messages)
        message = response["message"]

        if "tool_calls" not in message or not message.get("tool_calls"):
            return message.get("content") or ""

        tool_calls = message["tool_calls"]
        # Un solo mensaje assistant con todas las tool_calls (evita duplicar en el loop)
        messages.append(message)

        for tool_call in tool_calls:
            function_name = tool_call["function"]["name"]
            try:
                raw_args = tool_call["function"].get("arguments", {})
                arguments = _parse_tool_arguments(raw_args)
                function_to_call = TOOLS[function_name]
                result = function_to_call(**arguments)
                messages.append(
                    {
                        "role": "tool",
                        "name": function_name,
                        "content": result,
                    }
                )
            except Exception as ex:
                logger.error(f"Error ejecutando tool {function_name}: {ex}")
                messages.append(
                    {
                        "role": "tool",
                        "name": function_name,
                        "content": f"Error ejecutando función: {str(ex)}",
                    }
                )

        final_response = self.client.chat_with_tools(messages)
        return final_response["message"].get("content") or ""
