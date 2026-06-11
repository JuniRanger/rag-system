import pytest

from app.core.chunks import prepare_chunks_for_indexing, validate_indexed_chunk
from app.embeddings.base import BaseEmbeddingProvider


class FakeEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, dimension: int = 4):
        self._embedding_dimension = dimension
        self.batch_calls = 0

    @property
    def embedding_dimension(self) -> int:
        return self._embedding_dimension

    def embed_text(self, text: str) -> list[float]:
        return self._vector_for(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.batch_calls += 1
        return [self._vector_for(text) for text in texts]

    def _vector_for(self, text: str) -> list[float]:
        seed = sum(ord(char) for char in text) % 10
        return [float(seed + offset) for offset in range(self._embedding_dimension)]


def test_embed_chunks_generates_vectors_in_batch():
    provider = FakeEmbeddingProvider()
    chunks = [
        {"text": "primer fragmento", "metadata": {"filename": "a.txt", "chunk_index": 0}},
        {"text": "segundo fragmento", "metadata": {"filename": "a.txt", "chunk_index": 1}},
    ]

    result = provider.embed_chunks(chunks)

    assert provider.batch_calls == 1
    assert len(result) == 2
    assert all(len(chunk["embedding"]) == provider.embedding_dimension for chunk in result)
    assert all(chunk["metadata"]["chunk_id"] for chunk in prepare_chunks_for_indexing(result))


def test_embed_chunks_reuses_existing_embeddings():
    provider = FakeEmbeddingProvider()
    existing = [1.0, 2.0, 3.0, 4.0]
    chunks = [
        {
            "text": "fragmento reutilizado",
            "metadata": {"filename": "a.txt", "chunk_index": 0},
            "embedding": existing,
        }
    ]

    result = provider.embed_chunks(chunks)

    assert provider.batch_calls == 0
    assert result[0]["embedding"] == existing


def test_prepare_chunks_for_indexing_assigns_stable_chunk_id():
    chunks = prepare_chunks_for_indexing(
        [{"text": "hola mundo", "metadata": {"filename": "doc.txt", "chunk_index": 0}}]
    )

    chunk_id = chunks[0]["metadata"]["chunk_id"]
    assert chunk_id
    assert prepare_chunks_for_indexing(chunks)[0]["metadata"]["chunk_id"] == chunk_id


def test_validate_indexed_chunk_rejects_missing_embedding():
    with pytest.raises(ValueError, match="falta 'embedding'"):
        validate_indexed_chunk(
            {"text": "sin vector", "metadata": {"chunk_index": 0}},
            index=0,
            expected_dimension=4,
        )
