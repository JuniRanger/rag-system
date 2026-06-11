# app/tools/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseTool(ABC):
    """
    Clase abstracta de la que heredan todas las herramientas del sistema.
    """
    def __init__(self, schema: Dict[str, Any]):
        self.schema = schema
        self.name = schema["function"]["name"]

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """
        Lógica de ejecución de la herramienta. 
        Debe aceptar argumentos por palabra clave extraídos del LLM.
        """
        pass