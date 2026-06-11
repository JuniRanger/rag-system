from app.vectorstore.base import BaseVectorStoreProvider


class AzureCosmosVectorStoreProvider(BaseVectorStoreProvider):
    def __init__(self):
        raise NotImplementedError("Azure Cosmos vector store aún no está implementado.")

    def create_collection(self, recreate: bool = False, vector_size: int | None = None):
        raise NotImplementedError("Azure Cosmos vector store aún no está implementado.")

    def insert_points(self, chunks: list[dict]) -> int:
        raise NotImplementedError("Azure Cosmos vector store aún no está implementado.")

    def search(self, query_vector: list[float], top_k: int = None) -> list[dict]:
        raise NotImplementedError("Azure Cosmos vector store aún no está implementado.")

    def get_collection_info(self) -> dict:
        raise NotImplementedError("Azure Cosmos vector store aún no está implementado.")
