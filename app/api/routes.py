from fastapi import APIRouter, Depends, HTTPException
from app.api.schemas import (
    QueryRequest, QueryResponse,
    IngestRequest, IngestResponse,
    EvaluateRequest, EvaluateResponse,
    HealthResponse,
    SupabaseSyncRequest,
    SupabaseSyncResponse,
    SupabaseWebhookPayload,
    SupabaseWebhookResponse,
)
from app.api.supabase_auth import verify_sync_secret, verify_webhook_secret
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.supabase_sync import SupabaseSyncService
from app.vectorstore.indexer import VectorIndexer
from app.evaluation.evaluator import RAGEvaluator
from app.core.config import settings
from app.core.logger import logger
from app.core.providers import (
    create_rag_pipeline,
    get_embedding_provider,
    get_llm_provider,
    get_vector_store_provider,
)

router = APIRouter()


# ─── HEALTH CHECK ─────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["Sistema"])
async def health_check():
    """
    Verifica que todos los servicios están funcionando.
    Útil para saber si el sistema está listo antes de usarlo.
    """
    llm_provider = get_llm_provider()
    vector_store_provider = get_vector_store_provider()
    llm_ok = llm_provider.is_available()

    try:
        vector_store_provider.get_collection_info()
        vector_store_ok = True
    except Exception:
        vector_store_ok = False

    return HealthResponse(
        status="ok" if (llm_ok and vector_store_ok) else "degraded",
        ollama_available=llm_ok,
        qdrant_available=vector_store_ok,
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

        # Paso 2: Indexar en el almacén vectorial configurado
        indexer = VectorIndexer(
            embedding_provider=get_embedding_provider(),
            vector_store_provider=get_vector_store_provider(),
        )
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


# ─── SUPABASE SYNC ────────────────────────────────────────────────────────────

@router.post(
    "/sync",
    response_model=SupabaseSyncResponse,
    tags=["Supabase"],
    dependencies=[Depends(verify_sync_secret)],
)
async def sync_supabase(request: SupabaseSyncRequest):
    """
    Sincronización manual desde Supabase.

    - `incremental`: solo registros nuevos desde el último cursor guardado
    - `full`: toda la tabla configurada
    """
    logger.info(f"Request de sync Supabase | mode={request.mode} | table={request.table}")

    try:
        service = SupabaseSyncService()
        result = service.sync(
            table=request.table,
            mode=request.mode,
            recreate_collection=request.recreate_collection,
        )
        return SupabaseSyncResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error en sync Supabase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/webhooks/supabase",
    response_model=SupabaseWebhookResponse,
    tags=["Supabase"],
    dependencies=[Depends(verify_webhook_secret)],
)
async def supabase_webhook(payload: SupabaseWebhookPayload):
    """
    Webhook para ingerir automáticamente cada INSERT de Supabase.

    Configura en Supabase Dashboard → Database → Webhooks:
    - Event: INSERT
    - Table: tu tabla
    - URL: https://TU_API/api/v1/webhooks/supabase
    - Header: X-Webhook-Secret = SUPABASE_WEBHOOK_SECRET
    """
    logger.info(f"Webhook Supabase recibido | type={payload.type} | table={payload.table}")

    try:
        service = SupabaseSyncService()
        result = service.ingest_webhook_record(payload.model_dump())
        return SupabaseWebhookResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error en webhook Supabase: {e}")
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
        pipeline = create_rag_pipeline(use_reranker=request.use_reranker)

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


# ─── INFO DE COLECCIÓN ────────────────────────────────────────────────────────

@router.get("/collection/info", tags=["Sistema"])
async def collection_info():
    """Retorna estadísticas de la colección vectorial configurada."""
    try:
        vector_store_provider = get_vector_store_provider()
        info = vector_store_provider.get_collection_info()
        return {"success": True, "collection": info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
