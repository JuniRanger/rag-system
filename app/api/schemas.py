from pydantic import BaseModel, Field
from typing import Any, Literal, Optional

# Schemas RAG: app.rag.schemas (RAGRequest, RAGResponse, etc.)

# ─── REQUEST SCHEMAS (lo que recibe la API) ───────────────────────────────────

class IngestRequest(BaseModel):
    """Esquema para ingestar documentos."""
    source_path: str = Field(
        ...,
        description="Ruta al archivo o carpeta a ingestar"
    )
    recreate_collection: bool = Field(
        default=False,
        description="Si recrear la colección desde cero"
    )

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
        description="Ruta al dataset JSON. Si es null usa el dataset por defecto."
    )

class SupabaseSyncRequest(BaseModel):
    """Sincronización manual desde una tabla de Supabase."""
    table: Optional[str] = Field(
        default=None,
        description="Tabla a sincronizar. Si es null usa SUPABASE_TABLE del .env"
    )
    mode: Literal["full", "incremental"] = Field(
        default="incremental",
        description="full: toda la tabla | incremental: solo registros nuevos desde el último cursor"
    )
    recreate_collection: bool = Field(
        default=False,
        description="Si recrear la colección vectorial desde cero"
    )

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
    table: str
    schema: str = "public"
    record: Optional[dict[str, Any]] = None
    old_record: Optional[dict[str, Any]] = None

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