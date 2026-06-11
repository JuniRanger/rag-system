from collections.abc import Sequence

from app.core.documents import stable_chunk_id


def validate_ingested_chunk(chunk: dict, index: int):
    """Valida la estructura mínima de un chunk salido del pipeline de ingesta."""
    if not isinstance(chunk, dict):
        raise ValueError(f"Chunk inválido en posición {index}: se esperaba dict.")

    if not isinstance(chunk.get("text"), str) or not chunk["text"].strip():
        raise ValueError(f"Chunk inválido en posición {index}: falta 'text' no vacío.")

    if not isinstance(chunk.get("metadata"), dict):
        raise ValueError(f"Chunk inválido en posición {index}: falta 'metadata' como dict.")


def validate_indexed_chunk(chunk: dict, index: int, expected_dimension: int):
    """Valida que un chunk esté listo para persistirse en el vectorstore."""
    validate_ingested_chunk(chunk, index)

    embedding = chunk.get("embedding")
    if embedding is None:
        raise ValueError(f"Chunk inválido en posición {index}: falta 'embedding'.")

    if not isinstance(embedding, Sequence) or isinstance(embedding, (str, bytes)):
        raise ValueError(f"Chunk inválido en posición {index}: 'embedding' debe ser una secuencia numérica.")

    if len(embedding) != expected_dimension:
        raise ValueError(
            f"Chunk inválido en posición {index}: dimensión {len(embedding)} != {expected_dimension}."
        )

    if not all(isinstance(value, (int, float)) for value in embedding):
        raise ValueError(f"Chunk inválido en posición {index}: 'embedding' contiene valores no numéricos.")


def ensure_chunk_id(chunk: dict) -> str:
    """Asigna un ID estable al chunk si aún no existe en metadata."""
    metadata = chunk.setdefault("metadata", {})
    chunk_id = metadata.get("chunk_id")

    if not chunk_id:
        chunk_id = stable_chunk_id(chunk)
        metadata["chunk_id"] = chunk_id

    return chunk_id


def prepare_chunks_for_indexing(chunks: list[dict]) -> list[dict]:
    """Normaliza chunks de ingesta antes de generar embeddings o indexar."""
    if not chunks:
        raise ValueError("No hay chunks para indexar.")

    prepared = []
    for index, chunk in enumerate(chunks):
        validate_ingested_chunk(chunk, index)
        normalized = {
            "text": chunk["text"].strip(),
            "metadata": dict(chunk.get("metadata", {})),
        }
        if "embedding" in chunk and chunk["embedding"] is not None:
            normalized["embedding"] = chunk["embedding"]
        ensure_chunk_id(normalized)
        prepared.append(normalized)

    return prepared
