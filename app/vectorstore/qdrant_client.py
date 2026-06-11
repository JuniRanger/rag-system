"""Compatibilidad retroactiva. Usar get_vector_store_provider() en código nuevo."""
from app.core.providers import get_vector_store_provider
from app.vectorstore.base import BaseVectorStoreProvider
from app.vectorstore.providers.qdrant import QdrantVectorStoreProvider

QdrantManager = QdrantVectorStoreProvider
get_qdrant_manager = get_vector_store_provider

__all__ = ["QdrantManager", "QdrantVectorStoreProvider", "get_qdrant_manager"]
