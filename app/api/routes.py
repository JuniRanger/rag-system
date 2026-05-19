from fastapi import APIRouter, HTTPException
from app.api.schemas import (
    QueryRequest, QueryResponse,
    IngestRequest, IngestResponse,
    EvaluateRequest, EvaluateResponse,
    HealthResponse
)
from app.rag.pipeline import RAGPipeline
from app.ingestion.pipeline import IngestionPipeline
from app.vectorstore.indexer import VectorIndexer
from app.evaluation.evaluator import RAGEvaluator
from app.llm.client import OllamaClient
from app.vectorstore.qdrant_client import get_qdrant_manager
from app.core.config import settings
from app.core.logger import logger

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


# ─── INFO DE COLECCIÓN ────────────────────────────────────────────────────────

@router.get("/collection/info", tags=["Sistema"])
async def collection_info():
    """Retorna estadísticas de la colección vectorial en Qdrant."""
    try:
        info = qdrant_manager.get_collection_info()
        return {"success": True, "collection": info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))