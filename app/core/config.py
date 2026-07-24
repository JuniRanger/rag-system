from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

from app.core.llm_models import (
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_MODEL_FALLBACK,
)


def is_running_in_docker() -> bool:
    """True si el proceso corre dentro de un contenedor Docker/Podman."""
    return Path("/.dockerenv").exists() or Path("/run/.containerenv").exists()


class Settings(BaseSettings):
      # --- Aplicación ---
    APP_NAME: str = "RAG System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    PROVIDER_TYPE: str = "LOCAL"

    # --- Ollama (LLM generativo) ---
    # Override opcional. Si está vacío, se elige LOCAL o DOCKER automáticamente.
    OLLAMA_BASE_URL: str = ""
    OLLAMA_BASE_URL_LOCAL: str = "http://localhost:11434"
    OLLAMA_BASE_URL_DOCKER: str = "http://172.17.0.1:11434"
    OLLAMA_MODEL: str = DEFAULT_OLLAMA_MODEL
    OLLAMA_MODEL_FALLBACK: str = DEFAULT_OLLAMA_MODEL_FALLBACK
    OLLAMA_KEEP_ALIVE: str = "24h"

    # --- Qdrant Cloud (sin defaults para URL / API key) ---
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection_name: str = "documents"

    # --- Embeddings (cómo convertimos texto a números) ---
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 32

    # --- Reranker (CrossEncoder local; no usa Ollama) ---
    RERANKER_MODEL_NAME: str = "BAAI/bge-reranker-v2-m3"
    RERANKER_BATCH_SIZE: int = 16
    # Vacío = auto (cuda → mps → cpu)
    RERANKER_DEVICE: str = ""

    # --- Chunking (cómo dividimos los documentos) ---
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # --- Retrieval (cuántos fragmentos recuperamos) ---
    TOP_K: int = 10

    # --- Supabase (ingesta desde tabla) — valores en .env ---
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_TABLE: str = ""
    SUPABASE_ID_COLUMN: str = "id"
    SUPABASE_CURSOR_COLUMN: str = "id"
    SUPABASE_TEXT_COLUMNS: str = ""
    SUPABASE_WEBHOOK_SECRET: str = ""
    SUPABASE_SYNC_SECRET: str = ""
    # Tool calling en generación RAG (independiente de webhook/sync).
    # True → function calling en /query y /query/stream (rondas de tools + stream de la respuesta final).
    ENABLE_RAG_TOOLS: bool = True

    # --- API de citas (crearCitaAPI) ---
    CITAS_API_BASE_URL: str = "https://lacasadelosfrenos-api.onrender.com"

    # --- Rutas de datos ---
    RAW_DATA_PATH: str = "data/raw"
    PROCESSED_DATA_PATH: str = "data/processed"
    CHUNKS_DATA_PATH: str = "data/chunks"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def ollama_base_url(self) -> str:
        """
        URL efectiva de Ollama.

        Prioridad:
        1. OLLAMA_BASE_URL (override manual)
        2. OLLAMA_BASE_URL_DOCKER si corre en contenedor
        3. OLLAMA_BASE_URL_LOCAL en la máquina host
        """
        override = (self.OLLAMA_BASE_URL or "").strip()
        if override:
            return override.rstrip("/")
        if is_running_in_docker():
            return self.OLLAMA_BASE_URL_DOCKER.rstrip("/")
        return self.OLLAMA_BASE_URL_LOCAL.rstrip("/")

    @property
    def ollama_runtime(self) -> str:
        """Etiqueta del entorno Ollama activo: override | docker | local."""
        if (self.OLLAMA_BASE_URL or "").strip():
            return "override"
        return "docker" if is_running_in_docker() else "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
