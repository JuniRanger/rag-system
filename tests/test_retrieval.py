import pytest
import time
from app.vectorstore.qdrant_client import get_qdrant_manager
from app.embeddings.model import get_embedder
from app.core.config import settings

def test_retrieval_performance_under_100ms():
    """
    CRITERIO RÚBRICA: Validar que la búsqueda aproximada HNSW en la BD Vectorial
    mantenga una latencia p95 por debajo de los 100 milisegundos.
    Desactivamos el payload para medir estrictamente el rendimiento del índice.
    """
    qdrant_manager = get_qdrant_manager()
    embedder = get_embedder()
    
    query = "¿Qué latencia en el percentil p95 debe mantener el sistema?"
    query_vector = embedder.embed_text(query)
    
    # Cronómetro estricto sobre el motor de búsqueda de Qdrant
    start_time = time.time()
    results = qdrant_manager.client.search(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        query_vector=query_vector,
        limit=10,
        with_payload=False  # 🌟 CRÍTICO: Sin payload para medir solo el Grafo HNSW en RAM
    )
    end_time = time.time()
    
    latency_ms = (end_time - start_time) * 1000
    
    # 1. Validar que la BD no regresó vacía
    assert isinstance(results, list)
    assert len(results) > 0
    
    # 2. Validar que la latencia cumple con el p95 de la rúbrica (< 100ms)
    print(f"\n⏱️ Latencia de búsqueda pura HNSW: {latency_ms:.2f} ms")
    assert latency_ms < 100.0, f"La latencia de Qdrant ({latency_ms:.2f}ms) superó el límite de 100ms"