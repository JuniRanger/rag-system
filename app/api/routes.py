from fastapi import APIRouter, HTTPException, Header, Request
from app.api.schemas import (
    QueryRequest, QueryResponse,
    IngestRequest, IngestResponse,
    EvaluateRequest, EvaluateResponse,
    HealthResponse,
    SupabaseWebhookPayload,
    SupabaseWebhookResponse,
    SupabaseSyncRequest,
    SupabaseSyncResponse,
)
from app.rag.pipeline import RAGPipeline
from app.ingestion.pipeline import IngestionPipeline
from app.vectorstore.indexer import VectorIndexer
from app.evaluation.evaluator import RAGEvaluator
from app.llm.client import OllamaClient
from app.vectorstore.qdrant_client import get_qdrant_manager
from app.core.config import settings
from app.core.logger import logger
from app.ingestion.incremental import IncrementalIngestService, IncrementalIngestError
from app.ingestion.supabase_sync import (
    sync_table_to_qdrant,
    SupabaseSyncError,
    list_supabase_tables,
)
from app.embeddings.ollama_embedder import OllamaEmbeddingError

router = APIRouter()

# Instancias compartidas — se crean una vez al arrancar el servidor
rag_pipeline = RAGPipeline()
ollama_client = OllamaClient()
qdrant_manager = get_qdrant_manager()


# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["Sistema"])
async def health_check():
    """
    Verifica que todos los servicios están funcionando.
    Útil para saber si el sistema está listo antes de usarlo.
    """
    ollama_ok = ollama_client.is_available()

    try:
        qdrant_manager.get_collection_info()
        qdrant_ok = True
    except Exception:
        qdrant_ok = False

    return HealthResponse(
        status="ok" if (ollama_ok and qdrant_ok) else "degraded",
        ollama_available=ollama_ok,
        qdrant_available=qdrant_ok,
        model=settings.OLLAMA_MODEL,
        collection=settings.QDRANT_COLLECTION_NAME
    )


# ─── INGESTA ──────────────────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse, tags=["Ingesta"])
async def ingest_documents(request: IngestRequest):
    """
    Ingesta documentos al sistema RAG.
    Carga → limpia → fragmenta → embeddings → Qdrant.
    """
    logger.info(f"Request de ingesta: {request.source_path}")

    try:
        # Paso 1: Ejecutar pipeline de ingesta
        ingestion = IngestionPipeline()
        chunks = ingestion.run(request.source_path)

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No se encontraron documentos o el texto estaba vacío."
            )

        # Paso 2: Indexar en Qdrant
        indexer = VectorIndexer()
        collection_info = indexer.index_chunks(
            chunks,
            recreate=request.recreate_collection
        )

        return IngestResponse(
            success=True,
            message=f"Ingesta completada exitosamente",
            chunks_created=len(chunks),
            collection_info=collection_info
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en ingesta: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── CONSULTA RAG ─────────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse, tags=["RAG"])
async def query_rag(request: QueryRequest):
    """
    Consulta el sistema RAG con una pregunta en lenguaje natural.
    Retorna respuesta basada únicamente en los documentos indexados.
    """
    logger.info(f"Request de consulta: '{request.question}'")

    try:
        # Crear pipeline con configuración del request
        pipeline = RAGPipeline()
        pipeline.chain.use_reranker = request.use_reranker

        result = pipeline.query(request.question)

        return QueryResponse(
            success=result["success"],
            query=result["query"],
            answer=result["answer"],
            sources=result["sources"],
            metadata=result["metadata"]
        )

    except Exception as e:
        logger.error(f"Error en consulta RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── EVALUACIÓN ───────────────────────────────────────────────────────────────

@router.post("/evaluate", response_model=EvaluateResponse, tags=["Evaluación"])
async def evaluate_system(request: EvaluateRequest):
    """
    Corre la evaluación completa del sistema RAG.
    Calcula Context Precision, Recall, Faithfulness y Answer Relevancy.
    """
    logger.info("Request de evaluación del sistema")

    try:
        evaluator = RAGEvaluator()
        report = evaluator.evaluate(request.dataset_path)

        return EvaluateResponse(
            success=True,
            total_samples=report["total_samples"],
            average_metrics=report["average_metrics"],
            results=report["results"]
        )

    except Exception as e:
        logger.error(f"Error en evaluación: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── WEBHOOK SUPABASE (INGESTA INCREMENTAL) ───────────────────────────────────

@router.post(
    "/webhooks/supabase",
    response_model=SupabaseWebhookResponse,
    tags=["Ingesta"],
)
async def supabase_incremental_webhook(
    payload: SupabaseWebhookPayload,
    request: Request,
    x_webhook_secret: str | None = Header(default=None),
) -> SupabaseWebhookResponse:
    """
    Recibe INSERT de Supabase, genera embedding y hace upsert en Qdrant.
    Solo procesa type=INSERT; UPDATE/DELETE se ignoran con 200.
    """
    if settings.SUPABASE_WEBHOOK_SECRET:
        auth_header = request.headers.get("authorization", "")
        provided = x_webhook_secret or auth_header
        expected = settings.SUPABASE_WEBHOOK_SECRET.strip()
        # Supabase suele enviar "Bearer <jwt>"; aceptar header completo o solo el token
        token_from_header = (
            auth_header.split(" ", 1)[1].strip()
            if auth_header.lower().startswith("bearer ")
            else auth_header.strip()
        )
        expected_token = (
            expected.split(" ", 1)[1].strip()
            if expected.lower().startswith("bearer ")
            else expected
        )
        if provided not in (expected, expected_token) and token_from_header not in (
            expected,
            expected_token,
        ):
            raise HTTPException(status_code=401, detail="Webhook no autorizado")

    if payload.type != "INSERT":
        return SupabaseWebhookResponse(
            success=True,
            skipped=True,
            message=f"Evento {payload.type} ignorado (solo INSERT)",
            table=payload.table,
        )

    logger.info(
        f"Webhook Supabase recibido | type={payload.type} "
        f"schema={payload.schema_} table={payload.table}"
    )

    if payload.schema_ != settings.SUPABASE_SCHEMA:
        return SupabaseWebhookResponse(
            success=True,
            skipped=True,
            message=f"Schema '{payload.schema_}' ignorado (esperado: {settings.SUPABASE_SCHEMA})",
            table=payload.table,
        )

    service = IncrementalIngestService()
    try:
        result = await service.ingest_record(
            table=payload.table,
            record=payload.record_dict(),
        )
    except IncrementalIngestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OllamaEmbeddingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Webhook Supabase fallo: {exc}")
        raise HTTPException(
            status_code=503,
            detail=f"Qdrant u otro servicio no disponible: {exc}",
        ) from exc

    if result.get("skipped"):
        return SupabaseWebhookResponse(
            success=True,
            skipped=True,
            message=result.get("reason", "omitido"),
            table=payload.table,
        )

    return SupabaseWebhookResponse(
        success=True,
        skipped=False,
        message="Registro indexado en Qdrant",
        point_id=result.get("point_id"),
        supabase_id=result.get("supabase_id"),
        table=result.get("table"),
    )


@router.get("/sync/supabase/tables", tags=["Ingesta"])
async def list_supabase_tables_endpoint(schema: str | None = None):
    """Lista tablas del schema (default: SUPABASE_SCHEMA / public)."""
    try:
        tables = await list_supabase_tables(schema)
        profile = schema or settings.SUPABASE_SCHEMA
        return {"success": True, "schema": profile, "tables": tables}
    except SupabaseSyncError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/sync/supabase",
    response_model=SupabaseSyncResponse,
    tags=["Ingesta"],
)
async def sync_supabase_to_qdrant(
    request: SupabaseSyncRequest | None = None,
) -> SupabaseSyncResponse:
    """
    Fallback: lee TODAS las filas de Supabase e indexa en Qdrant.
    Usalo si insertaste en Supabase pero el webhook no alcanzo tu API (ej. localhost).
    Flujo: insert en Supabase -> POST /sync/supabase -> POST /query
    """
    table = request.table if request else None
    schema = request.schema_name if request else None
    try:
        result = await sync_table_to_qdrant(table, schema)
    except SupabaseSyncError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Sync Supabase fallo: {exc}")
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return SupabaseSyncResponse(
        success=True,
        schema=result["schema"],
        table=result["table"],
        total_rows=result["total_rows"],
        indexed=result["indexed"],
        skipped=result["skipped"],
        errors=result["errors"],
    )


@router.post("/sync/supabase/purge-legacy", tags=["Ingesta"])
async def purge_legacy_supabase_index():
    """
    Borra indexaciones viejas (ej. productos) que contaminan /query.
    Luego ejecuta POST /sync/supabase para reindexar documentos_tecnicos.
    """
    try:
        qdrant_manager.delete_by_payload_match("supabase_table", "productos")
        qdrant_manager.delete_by_payload_match("filename", "supabase:productos")
        info = qdrant_manager.get_collection_info()
        return {
            "success": True,
            "message": "Index legacy productos eliminada",
            "collection": info,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# ─── INFO DE COLECCIÓN ────────────────────────────────────────────────────────

@router.get("/collection/info", tags=["Sistema"])
async def collection_info():
    """Retorna estadísticas de la colección vectorial en Qdrant."""
    try:
        info = qdrant_manager.get_collection_info()
        return {"success": True, "collection": info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    