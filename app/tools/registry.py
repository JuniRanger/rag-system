# app/tools/registry.py
from typing import Dict, List, Any, Optional
from app.tools.base import BaseTool

class ToolRegistry:
    """
    Registro centralizado (Singleton) para almacenar y exponer 
    las herramientas disponibles para los agentes de IA.
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Registra una nueva herramienta en el sistema."""
        if tool.name in self._tools:
            raise ValueError(f"La herramienta '{tool.name}' ya se encuentra registrada.")
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Recupera una herramienta por su nombre."""
        return self._tools.get(name)

    def get_ollama_schemas(self) -> List[Dict[str, Any]]:
        """
        Devuelve el catálogo completo de herramientas con el formato 
        JSON nativo que Ollama y modelos como Qwen esperan.
        """
        return [tool.schema for tool in self._tools.values()]

    def list_tool_names(self) -> List[str]:
        """Devuelve una lista de los nombres de todas las herramientas registradas."""
        return list(self._tools.keys())

# Instancia única global para todo el ciclo de vida de la aplicación
tool_registry = ToolRegistry()