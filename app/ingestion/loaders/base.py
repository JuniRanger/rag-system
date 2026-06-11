from abc import ABC, abstractmethod
from typing import Any


class BaseLoader(ABC):
    """
    Contrato base para cualquier fuente de datos.

    Cada documento debe tener esta forma:
    {
        "text": "...",
        "metadata": {...}
    }
    """

    @abstractmethod
    def load(self) -> list[dict[str, Any]]:
        """
        Debe retornar una lista de documentos normalizados.
        """
        raise NotImplementedError
