from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.sanitize import (
    sanitize_identifier,
    sanitize_relative_path,
    sanitize_text,
)

# Schemas RAG: app.rag.schemas (RAGRequest, RAGResponse, etc.)

# ─── REQUEST SCHEMAS (lo que recibe la API) ───────────────────────────────────

class IngestRequest(BaseModel):
    """Esquema para ingestar documentos."""
    source_path: str = Field(
        ...,
        description="Ruta relativa al archivo o carpeta a ingestar",
        max_length=512,
    )
    recreate_collection: bool = Field(
        default=False,
        description="Si recrear la colección desde cero"
    )

    @field_validator("source_path")
    @classmethod
    def validate_source_path(cls, value: str) -> str:
        return sanitize_relative_path(value, field="source_path")

    class Config:
        json_schema_extra = {
            "example": {
                "source_path": "data/raw",
                "recreate_collection": False
            }
        }

class EvaluateRequest(BaseModel):
    """Esquema para correr evaluación del sistema."""
    dataset_path: Optional[str] = Field(
        default=None,
        description="Ruta relativa al dataset JSON. Si es null usa el dataset por defecto.",
        max_length=512,
    )

    @field_validator("dataset_path")
    @classmethod
    def validate_dataset_path(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        return sanitize_relative_path(value, field="dataset_path")

class SupabaseSyncRequest(BaseModel):
    """Sincronización manual desde una tabla de Supabase."""
    table: Optional[str] = Field(
        default=None,
        description="Tabla a sincronizar. Si es null usa SUPABASE_TABLE del .env",
        max_length=63,
    )
    mode: Literal["full", "incremental"] = Field(
        default="incremental",
        description="full: toda la tabla | incremental: solo registros nuevos desde el último cursor"
    )
    recreate_collection: bool = Field(
        default=False,
        description="Si recrear la colección vectorial desde cero"
    )

    @field_validator("table")
    @classmethod
    def validate_table(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value == "":
            return None
        return sanitize_identifier(value, field="table")

    class Config:
        json_schema_extra = {
            "example": {
                "table": None,
                "mode": "incremental",
                "recreate_collection": False,
            }
        }

class SupabaseWebhookPayload(BaseModel):
    """Payload enviado por Supabase Database Webhooks."""
    type: str = Field(..., description="Tipo de evento: INSERT, UPDATE, DELETE")
    table: str = Field(..., max_length=63)
    schema: str = Field(default="public", max_length=63)
    record: Optional[dict[str, Any]] = None
    old_record: Optional[dict[str, Any]] = None

    @field_validator("table", "schema")
    @classmethod
    def validate_identifiers(cls, value: str) -> str:
        return sanitize_identifier(value, field="identifier")

    @field_validator("type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        return sanitize_text(value, field="type", max_length=32).upper()

# ─── RESPONSE SCHEMAS (lo que retorna la API) ─────────────────────────────────

class IngestResponse(BaseModel):
    """Respuesta de una ingesta de documentos."""
    success: bool
    message: str
    chunks_created: int
    collection_info: dict

class EvaluateResponse(BaseModel):
    """Respuesta de la evaluación del sistema."""
    success: bool
    total_samples: int
    average_metrics: dict
    results: list[dict]

class HealthResponse(BaseModel):
    """Estado del sistema."""
    status: str
    ollama_available: bool
    qdrant_available: bool
    model: str
    collection: str

class SupabaseSyncResponse(BaseModel):
    """Respuesta de sincronización manual con Supabase."""
    success: bool
    message: str
    table: str
    mode: Optional[str] = None
    records_processed: int
    chunks_created: int
    collection_info: dict
    sync_state: dict

class SupabaseWebhookResponse(BaseModel):
    """Respuesta del webhook de Supabase."""
    success: bool
    message: str
    record_id: Optional[Any] = None
    chunks_created: int = 0
    collection_info: Optional[dict] = None