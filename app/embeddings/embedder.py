"""API pública del módulo de embeddings."""
from app.core.providers import get_embedding_provider
from app.embeddings.base import BaseEmbeddingProvider
from app.embeddings.providers.sentence_transformer import SentenceTransformerEmbeddingProvider

get_embedder = get_embedding_provider
Embedder = SentenceTransformerEmbeddingProvider

__all__ = [
    "BaseEmbeddingProvider",
    "Embedder",
    "SentenceTransformerEmbeddingProvider",
    "get_embedder",
]
