# app/tools/executor.py
import logging
from typing import Dict, Any, Optional
from app.tools.registry import tool_registry

logger = logging.getLogger("app.tools.executor")

class ToolExecutor:
    """
    Orquestador encargado de interceptar las llamadas del modelo,
    mapear los argumentos y ejecutar las herramientas de manera segura.
    """
    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Busca y ejecuta una herramienta controlando los errores en tiempo de ejecución.
        """
        tool = tool_registry.get_tool(tool_name)
        
        if not tool:
            error_msg = f"Error: La herramienta '{tool_name}' no existe en el registro."
            logger.error(error_msg)
            return {"status": "error", "output": error_msg}

        try:
            logger.info(f"Ejecutando herramienta: {tool_name} con argumentos: {arguments}")
            
            # Ejecutamos el método run desempaquetando los argumentos seguros del LLM
            output = tool.run(**arguments)
            
            return {
                "status": "success",
                "tool": tool_name,
                "output": output
            }
            
        except TypeError as te:
            # Captura si el LLM mandó argumentos de más o de menos que rompen la firma del método run
            error_msg = f"Error de firma en '{tool_name}': Argumentos inválidos provistos por el modelo. {str(te)}"
            logger.error(error_msg)
            return {"status": "error", "output": error_msg}
            
        except Exception as e:
            # Control de errores general para asegurar que tu backend de FastAPI nunca se caiga
            error_msg = f"Excepción interna ejecutando '{tool_name}': {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"status": "error", "output": error_msg}

# Instancia única global para el inyector de dependencias o tu service layer
tool_executor = ToolExecutor()