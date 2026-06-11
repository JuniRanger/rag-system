from app.embeddings.base import BaseEmbeddingProvider


class AzureOpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self):
        raise NotImplementedError("Azure OpenAI embeddings aún no está implementado.")

    @property
    def embedding_dimension(self) -> int:
        raise NotImplementedError("Azure OpenAI embeddings aún no está implementado.")

    def embed_text(self, text: str) -> list[float]:
        raise NotImplementedError("Azure OpenAI embeddings aún no está implementado.")

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("Azure OpenAI embeddings aún no está implementado.")
