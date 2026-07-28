# app/tools/executor.py
import inspect
import logging
from typing import Any, Dict

from app.tools.registry import tool_registry

logger = logging.getLogger("app.tools.executor")


class ToolExecutor:
    """
    Orquestador encargado de interceptar las llamadas del modelo,
    mapear los argumentos y ejecutar las herramientas de manera segura.
    """

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Busca y ejecuta una herramienta controlando los errores en tiempo de ejecución.

        Soporta ``run`` síncrono o ``async def run`` (p. ej. tools HTTP con AsyncClient).
        """
        tool = tool_registry.get_tool(tool_name)

        if not tool:
            error_msg = f"Error: La herramienta '{tool_name}' no existe en el registro."
            logger.error(error_msg)
            return {"status": "error", "output": error_msg}

        try:
            logger.info(f"Ejecutando herramienta: {tool_name} con argumentos: {arguments}")

            output = tool.run(**arguments)
            if inspect.isawaitable(output):
                output = await output

            return {
                "status": "success",
                "tool": tool_name,
                "output": output,
            }

        except TypeError as te:
            error_msg = (
                f"Error de firma en '{tool_name}': Argumentos inválidos "
                f"provistos por el modelo. {str(te)}"
            )
            logger.error(error_msg)
            return {"status": "error", "output": error_msg}

        except Exception as e:
            error_msg = f"Excepción interna ejecutando '{tool_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"status": "error", "output": error_msg}


tool_executor = ToolExecutor()
