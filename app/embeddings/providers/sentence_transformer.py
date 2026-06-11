from sentence_transformers import SentenceTransformer

from app.core.config import settings
from app.core.logger import logger
from app.embeddings.base import BaseEmbeddingProvider


class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self):
        logger.info(f"Cargando modelo de embeddings: {settings.EMBEDDING_MODEL_NAME}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        self._embedding_dimension = self.model.get_sentence_embedding_dimension()

        if self._embedding_dimension != settings.EMBEDDING_DIMENSION:
            raise ValueError(
                f"Dimensión de embeddings inconsistente: modelo={self._embedding_dimension}, "
                f"config={settings.EMBEDDING_DIMENSION}."
            )

        logger.info(
            f"Modelo de embeddings listo | dimensión={self._embedding_dimension} | "
            f"batch_size={settings.EMBEDDING_BATCH_SIZE}"
        )

    @property
    def embedding_dimension(self) -> int:
        return self._embedding_dimension

    def embed_text(self, text: str) -> list[float]:
        """Convierte un texto en un vector de números."""
        if not text or not text.strip():
            raise ValueError("No se puede generar embedding para texto vacío.")

        vector = self.model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Convierte múltiples textos en vectores de una vez.
        Mucho más eficiente que llamar embed_text en un loop.
        """
        if not texts:
            return []

        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("No se pueden generar embeddings para textos vacíos.")

        logger.debug(f"Generando embeddings para {len(texts)} textos")
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            show_progress_bar=False,
        )
        return vectors.tolist()
