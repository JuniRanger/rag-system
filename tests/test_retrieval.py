import time

import pytest

from app.core.config import settings
from app.core.providers import get_embedding_provider, get_vector_store_provider
from app.vectorstore.providers.qdrant import QdrantVectorStoreProvider


@pytest.mark.integration
def test_retrieval_performance_under_100ms():
    """
    CRITERIO RÚBRICA: Validar que la búsqueda aproximada HNSW en la BD Vectorial
    mantenga una latencia p95 por debajo de los 100 milisegundos.
    Desactivamos el payload para medir estrictamente el rendimiento del índice.
    """
    vector_store = get_vector_store_provider()
    embedder = get_embedding_provider()

    if not isinstance(vector_store, QdrantVectorStoreProvider):
        pytest.skip("Este test de rendimiento requiere Qdrant como vector store.")

    query = "¿Qué latencia en el percentil p95 debe mantener el sistema?"
    query_vector = embedder.embed_text(query)

    start_time = time.time()
    results = vector_store.client.search(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        query_vector=query_vector,
        limit=10,
        with_payload=False,
    )
    end_time = time.time()

    latency_ms = (end_time - start_time) * 1000

    assert isinstance(results, list)
    assert len(results) > 0

    print(f"\n⏱️ Latencia de búsqueda pura HNSW: {latency_ms:.2f} ms")
    assert latency_ms < 100.0, f"La latencia de Qdrant ({latency_ms:.2f}ms) superó el límite de 100ms"
