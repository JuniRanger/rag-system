from sentence_transformers import SentenceTransformer
from app.core.config import settings
from app.core.logger import logger

class Embedder:
    def __init__(self):
        logger.info(f"Cargando modelo de embeddings: {settings.EMBEDDING_MODEL_NAME}")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        logger.info("Modelo de embeddings listo")

    def embed_text(self, text: str) -> list[float]:
        """Convierte un texto en un vector de números."""
        vector = self.model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Convierte múltiples textos en vectores de una vez.
        Mucho más eficiente que llamar embed_text en un loop.
        """
        logger.debug(f"Generando embeddings para {len(texts)} textos")
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,        # Procesa 32 textos a la vez para no sobrecargar RAM
            show_progress_bar=True
        )
        return vectors.tolist()

    def embed_chunks(self, chunks: list[dict]) -> list[dict]:
        """Agrega el vector a cada chunk del pipeline de ingesta."""
        texts = [chunk["text"] for chunk in chunks]
        vectors = self.embed_batch(texts)

        for chunk, vector in zip(chunks, vectors):
            chunk["embedding"] = vector

        logger.info(f"Embeddings generados: {len(chunks)} vectores de {settings.EMBEDDING_DIMENSION} dimensiones")
        return chunks