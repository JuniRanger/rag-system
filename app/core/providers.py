from functools import lru_cache

from app.core.config import settings
from app.embeddings.base import BaseEmbeddingProvider
from app.llm.base import BaseLLMProvider
from app.vectorstore.base import BaseVectorStoreProvider


@lru_cache()
def get_embedding_provider() -> BaseEmbeddingProvider:
    provider_type = settings.PROVIDER_TYPE.upper()

    if provider_type == "LOCAL":
        from app.embeddings.providers.sentence_transformer import SentenceTransformerEmbeddingProvider

        return SentenceTransformerEmbeddingProvider()

    if provider_type == "AZURE":
        from app.embeddings.providers.azure_openai import AzureOpenAIEmbeddingProvider

        return AzureOpenAIEmbeddingProvider()

    raise ValueError(f"PROVIDER_TYPE no soportado para embeddings: {settings.PROVIDER_TYPE}")


@lru_cache()
def get_vector_store_provider() -> BaseVectorStoreProvider:
    provider_type = settings.PROVIDER_TYPE.upper()

    if provider_type == "LOCAL":
        from app.vectorstore.providers.qdrant import QdrantVectorStoreProvider

        return QdrantVectorStoreProvider()

    if provider_type == "AZURE":
        from app.vectorstore.providers.azure_cosmos import AzureCosmosVectorStoreProvider

        return AzureCosmosVectorStoreProvider()

    raise ValueError(f"PROVIDER_TYPE no soportado para vector store: {settings.PROVIDER_TYPE}")


@lru_cache()
def get_llm_provider() -> BaseLLMProvider:
    provider_type = settings.PROVIDER_TYPE.upper()

    if provider_type == "LOCAL":
        from app.llm.providers.ollama import OllamaLLMProvider

        return OllamaLLMProvider()

    if provider_type == "AZURE":
        from app.llm.providers.azure_gpt import AzureGPTLLMProvider

        return AzureGPTLLMProvider()

    raise ValueError(f"PROVIDER_TYPE no soportado para LLM: {settings.PROVIDER_TYPE}")


def get_provider_bundle() -> tuple[BaseEmbeddingProvider, BaseVectorStoreProvider, BaseLLMProvider]:
    return (
        get_embedding_provider(),
        get_vector_store_provider(),
        get_llm_provider(),
    )


def create_rag_pipeline(use_reranker: bool = True):
    from app.rag.pipeline import RAGPipeline

    embedding_provider, vector_store_provider, llm_provider = get_provider_bundle()
    return RAGPipeline(
        embedding_provider=embedding_provider,
        vector_store_provider=vector_store_provider,
        llm_provider=llm_provider,
        use_reranker=use_reranker,
    )
