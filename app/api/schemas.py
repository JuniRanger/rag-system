from pydantic import BaseModel, Field
from typing import Optional

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