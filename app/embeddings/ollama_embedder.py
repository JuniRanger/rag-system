"""Embeddings individuales via API HTTP de Ollama (async)."""
import httpx
from app.core.config import settings
from app.core.logger import logger


class OllamaEmbeddingError(Exception):
    """Fallo al generar embedding en Ollama."""


class OllamaEmbedder:
    def __init__(self) -> None:
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model = settings.OLLAMA_EMBEDDING_MODEL

    async def embed_text(self, text: str) -> list[float]:
        """POST /api/embeddings — un vector por registro nuevo."""
        payload = {"model": self.model, "prompt": text}
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            logger.error(f"Ollama embeddings HTTP error: {exc}")
            raise OllamaEmbeddingError(f"Ollama no respondio: {exc}") from exc

        vector = data.get("embedding")
        if not vector:
            raise OllamaEmbeddingError("Respuesta de Ollama sin campo 'embedding'")

        if len(vector) != settings.EMBEDDING_DIMENSION:
            raise OllamaEmbeddingError(
                f"Dimension {len(vector)} != EMBEDDING_DIMENSION={settings.EMBEDDING_DIMENSION}. "
                "Alinea OLLAMA_EMBEDDING_MODEL con la coleccion Qdrant o reindexa."
            )

        return vector
