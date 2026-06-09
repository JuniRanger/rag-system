from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Any, Literal, Optional
from uuid import UUID

# ─── REQUEST SCHEMAS (lo que recibe la API) ───────────────────────────────────

class QueryRequest(BaseModel):
    """Esquema para consultas al sistema RAG."""
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Pregunta del usuario"
    )
    use_reranker: bool = Field(
        default=True,
        description="Si usar reranking para mejorar precisión"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "question": "¿Qué es una base de datos vectorial?",
                "use_reranker": True
            }
        }

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

# ─── RESPONSE SCHEMAS (lo que retorna la API) ─────────────────────────────────

class QueryResponse(BaseModel):
    """Respuesta de una consulta RAG."""
    success: bool
    query: str
    answer: str
    sources: list[str]
    metadata: dict

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


# --- Supabase: rag.documentos_tecnicos ---

class DocumentoTecnicoRecordSchema(BaseModel):
    """Espejo del DDL rag.documentos_tecnicos."""

    model_config = ConfigDict(extra="allow")

    id: UUID | None = None
    vehiculo_marca: str | None = None
    vehiculo_modelo: str | None = None
    categoria_problema: str | None = None
    problema: str | None = None
    diagnostico: str | None = None
    solucion: str | None = None
    ecu_data: str | None = None
    severidad: str | None = None
    repair_status: str | None = None
    historial_servicio: str | None = None
    creado_en: str | None = None


class SupabaseWebhookPayload(BaseModel):
    """Payload de Supabase Database Webhooks."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    type: Literal["INSERT", "UPDATE", "DELETE"]
    table: str
    schema_: str = Field(default="public", alias="schema")
    record: DocumentoTecnicoRecordSchema | dict[str, Any]
    old_record: DocumentoTecnicoRecordSchema | dict[str, Any] | None = None

    @field_validator("table")
    @classmethod
    def normalize_table(cls, value: str) -> str:
        return value.strip()

    def record_dict(self) -> dict[str, Any]:
        if isinstance(self.record, DocumentoTecnicoRecordSchema):
            return self.record.model_dump(exclude_none=True)
        return self.record


class SupabaseWebhookResponse(BaseModel):
    success: bool
    skipped: bool = False
    message: str
    point_id: str | None = None
    supabase_id: str | None = None
    table: str | None = None


class SupabaseSyncRequest(BaseModel):
    """Sync manual: trae filas de public.documentos_tecnicos e indexa en Qdrant."""

    model_config = ConfigDict(populate_by_name=True)

    table: str | None = Field(
        default=None,
        description="Tabla; default SUPABASE_SYNC_TABLE (documentos_tecnicos)",
    )
    schema_name: str | None = Field(
        default=None,
        alias="schema",
        description="Schema Postgres; default SUPABASE_SCHEMA (public)",
    )


class SupabaseSyncResponse(BaseModel):
    success: bool
    schema: str
    table: str
    total_rows: int
    indexed: int
    skipped: int
    errors: list[str]