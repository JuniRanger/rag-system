from app.llm.client import OllamaClient
from app.tools.tools_registry import TOOLS
from app.core.logger import logger


class ToolHandler:

    def __init__(self):
        self.client = OllamaClient()

    def execute(self, messages):

        response = self.client.chat_with_tools(messages)

        message = response["message"]

        # =========================
        # SI NO HAY TOOL CALL
        # =========================

        if "tool_calls" not in message:
            return message["content"]

        tool_calls = message["tool_calls"]

        # =========================
        # EJECUTAR TOOLS
        # =========================

        for tool_call in tool_calls:

            function_name = tool_call["function"]["name"]

            arguments = tool_call["function"]["arguments"]

            try:

                function_to_call = TOOLS[function_name]

                result = function_to_call(**arguments)

                messages.append(message)

                messages.append({
                    "role": "tool",
                    "name": function_name,
                    "content": result
                })

            except Exception as ex:

                logger.error(
                    f"Error ejecutando tool {function_name}: {ex}"
                )

                messages.append({
                    "role": "tool",
                    "name": function_name,
                    "content": (
                        f"Error ejecutando función: {str(ex)}"
                    )
                })

        # =========================
        # RESPUESTA FINAL DEL LLM
        # =========================

        final_response = self.client.chat_with_tools(messages)

        return final_response["message"]["content"]