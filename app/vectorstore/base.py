from abc import ABC, abstractmethod


class BaseVectorStoreProvider(ABC):
    @abstractmethod
    def create_collection(self, recreate: bool = False, vector_size: int | None = None):
        """Crea o prepara la colección donde se guardarán los vectores."""
        raise NotImplementedError

    @abstractmethod
    def insert_points(self, chunks: list[dict]) -> int:
        """Guarda vectores y payloads en el almacén vectorial. Retorna puntos insertados."""
        raise NotImplementedError

    @abstractmethod
    def search(self, query_vector: list[float], top_k: int = None) -> list[dict]:
        """Busca vectores similares al vector de consulta."""
        raise NotImplementedError

    @abstractmethod
    def get_collection_info(self) -> dict:
        """Retorna estadísticas de la colección."""
        raise NotImplementedError
