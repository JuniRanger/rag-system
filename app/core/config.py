from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
      # --- Aplicación ---
    APP_NAME: str = "RAG System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # --- Ollama (tu LLM local) ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    OLLAMA_KEEP_ALIVE: str = "24h"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    # local = sentence-transformers (misma dimension que /ingest); ollama = API embeddings
    INCREMENTAL_EMBEDDING_BACKEND: str = "ollama"

    # --- Supabase webhook (ingesta incremental) ---
    SUPABASE_WEBHOOK_SECRET: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_SCHEMA: str = "public"
    SUPABASE_SYNC_TABLE: str = "documentos_tecnicos"
    SUPABASE_RECORD_ID_FIELD: str = "id"
    SUPABASE_RECORD_TEXT_FIELD: str = "problema"
    SUPABASE_RECORD_TEXT_FIELD_ALT: str = (
        "vehiculo_marca,vehiculo_modelo,categoria_problema,diagnostico,solucion,"
        "ecu_data,severidad,repair_status,historial_servicio"
    )
    SUPABASE_WEBHOOK_ALLOWED_TABLES: str = "documentos_tecnicos"

    # --- Qdrant (tu base de datos vectorial) ---
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "documents"

    # --- Embeddings (cómo convertimos texto a números) ---
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSION: int = 384

    # --- Chunking (cómo dividimos los documentos) ---
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # --- Retrieval (cuántos fragmentos recuperamos) ---
    TOP_K: int = 10
    # Filtra /query a esta tabla Supabase (documentos_tecnicos); vacio = sin filtro
    RAG_SEARCH_SUPABASE_TABLE: str = "documentos_tecnicos"
    # Umbral cosine similarity; multilingual suele puntuar mas bajo (~0.25-0.35)
    RAG_SCORE_THRESHOLD: float = 0.25

    # --- Rutas de datos ---
    RAW_DATA_PATH: str = "data/raw"
    PROCESSED_DATA_PATH: str = "data/processed"
    CHUNKS_DATA_PATH: str = "data/chunks"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def supabase_text_field_candidates(self) -> list[str]:
        """Campos de texto a probar; ALT admite varios separados por coma."""
        fields: list[str] = []
        if self.SUPABASE_RECORD_TEXT_FIELD:
            fields.append(self.SUPABASE_RECORD_TEXT_FIELD)
        if self.SUPABASE_RECORD_TEXT_FIELD_ALT:
            for part in self.SUPABASE_RECORD_TEXT_FIELD_ALT.split(","):
                name = part.strip()
                if name and name not in fields:
                    fields.append(name)
        return fields

    def supabase_allowed_tables(self) -> list[str]:
        raw = (self.SUPABASE_WEBHOOK_ALLOWED_TABLES or "").strip()
        if not raw:
            return []
        return [t.strip() for t in raw.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()