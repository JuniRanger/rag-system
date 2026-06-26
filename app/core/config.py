from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
      # --- Aplicación ---
    APP_NAME: str = "RAG System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    PROVIDER_TYPE: str = "LOCAL"

    # --- Ollama (tu LLM local) ---
    OLLAMA_BASE_URL: str = "http://172.17.0.1:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"
    OLLAMA_KEEP_ALIVE: str = "24h"

    # --- Qdrant (tu base de datos vectorial) ---
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "documents"

    # --- Embeddings (cómo convertimos texto a números) ---
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 32

    # --- Chunking (cómo dividimos los documentos) ---
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # --- Retrieval (cuántos fragmentos recuperamos) ---
    TOP_K: int = 5

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
    # False → streaming habilitado; True → /query usa herramientas Supabase, /query/stream no.
    ENABLE_RAG_TOOLS: bool = False

    # --- Rutas de datos ---
    RAW_DATA_PATH: str = "data/raw"
    PROCESSED_DATA_PATH: str = "data/processed"
    CHUNKS_DATA_PATH: str = "data/chunks"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        
@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
