import asyncio
from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.core.chunks import validate_ingested_chunk
from app.core.logger import logger


class BaseEmbeddingProvider(ABC):
    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Dimensión de los vectores producidos por el provider."""
        raise NotImplementedError

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Convierte un texto en un vector de números."""
        raise NotImplementedError

    async def embed_text_async(self, text: str) -> list[float]:
        """Versión asíncrona de embed_text."""
        return await asyncio.to_thread(self.embed_text, text)

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Convierte múltiples textos en vectores."""
        raise NotImplementedError

    def embed_chunks(self, chunks: list[dict]) -> list[dict]:
        """
        Agrega el vector a cada chunk del pipeline de ingesta.
        Solo procesa chunks con estructura {text, metadata}; reutiliza embeddings existentes.
        """
        if not chunks:
            logger.info("No hay chunks para generar embeddings")
            return chunks

        pending_chunks = []
        pending_texts = []

        for index, chunk in enumerate(chunks):
            validate_ingested_chunk(chunk, index)
            embedding = chunk.get("embedding")

            if embedding is not None:
                self._validate_embedding(embedding, index)
                continue

            pending_chunks.append(chunk)
            pending_texts.append(chunk["text"])

        if not pending_chunks:
            logger.info(f"Todos los chunks ya tenían embeddings válidos: {len(chunks)}")
            return chunks

        logger.info(f"Generando embeddings para {len(pending_chunks)} chunks sin vector")
        try:
            vectors = self.embed_batch(pending_texts)
        except Exception as exc:
            logger.error(f"Error generando embeddings en batch: {exc}")
            raise

        if len(vectors) != len(pending_chunks):
            raise ValueError(
                f"El provider devolvió {len(vectors)} embeddings para {len(pending_chunks)} chunks."
            )

        for chunk, vector in zip(pending_chunks, vectors):
            self._validate_embedding(vector)
            chunk["embedding"] = vector

        logger.info(
            f"Embeddings listos: {len(chunks)} chunks | "
            f"nuevos={len(pending_chunks)} | reutilizados={len(chunks) - len(pending_chunks)} | "
            f"dimensión={self.embedding_dimension}"
        )
        return chunks

    def _validate_embedding(self, embedding: Sequence[float], index: int | None = None):
        location = f" en posición {index}" if index is not None else ""

        if not isinstance(embedding, Sequence) or isinstance(embedding, (str, bytes)):
            raise ValueError(f"Embedding inválido{location}: se esperaba una secuencia numérica.")

        if len(embedding) != self.embedding_dimension:
            raise ValueError(
                f"Embedding inválido{location}: dimensión {len(embedding)} != {self.embedding_dimension}."
            )

        if not all(isinstance(value, (int, float)) for value in embedding):
            raise ValueError(f"Embedding inválido{location}: contiene valores no numéricos.")
