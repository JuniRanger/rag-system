import pytest
from app.ingestion.processors.chunker import TextChunker

def test_chunking_integrity():
    """
    CRITERIO RÚBRICA: Validar la correcta fragmentación (chunking) de documentos
    asegurando que los fragmentos mantengan la coherencia del texto original.
    """
    text_sample = (
        "El sistema debe mantener una latencia en el percentil 95 (p95) por debajo de los 100 milisegundos. "
        "Si la configuración de la base de datos vectorial es volátil la calificación se considera insuficiente."
    )
    
    chunker = TextChunker()
    chunker.chunk_size = 120
    chunker.chunk_overlap = 20
    chunks = chunker.chunk(text_sample)
    
    assert isinstance(chunks, list)
    assert len(chunks) > 1
    
    # Validar que los datos core siguen existiendo tras el split
    full_text = " ".join([c["text"] for c in chunks]).lower()
    assert "latencia" in full_text
    assert "p95" in full_text
    assert "volátil" in full_text

    for chunk in chunks:
        assert "text" in chunk
        assert isinstance(chunk["metadata"], dict)
        assert "chunk_index" in chunk["metadata"]
        assert chunk["metadata"]["chunk_id"]
