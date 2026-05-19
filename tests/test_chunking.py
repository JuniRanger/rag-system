import pytest
from app.ingestion.chunker import Chunker  # Ajusta según tu archivo real

def test_chunking_integrity():
    """
    CRITERIO RÚBRICA: Validar la correcta fragmentación (chunking) de documentos
    asegurando que los fragmentos mantengan la coherencia del texto original.
    """
    text_sample = (
        "El sistema debe mantener una latencia en el percentil 95 (p95) por debajo de los 100 milisegundos. "
        "Si la configuración de la base de datos vectorial es volátil la calificación se considera insuficiente."
    )
    
    chunker = Chunker(max_chars=120, overlap=20)
    chunks = chunker.split_text(text_sample)
    
    assert isinstance(chunks, list)
    assert len(chunks) > 1
    
    # Validar que los datos core siguen existiendo tras el split
    full_text = " ".join([c["text"] for c in chunks]).lower()
    assert "latencia" in full_text
    assert "p95" in full_text
    assert "volátil" in full_text