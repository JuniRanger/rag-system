"""Compatibilidad retroactiva. Usar get_embedding_provider() en código nuevo."""
from app.core.providers import get_embedding_provider
from app.embeddings.base import BaseEmbeddingProvider

get_embedder = get_embedding_provider

__all__ = ["get_embedder", "BaseEmbeddingProvider"]
