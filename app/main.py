from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.routes import router
from app.core.config import settings
from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Al arrancar: precargar todo en memoria ──
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    
    logger.info("Precargando modelo de embeddings en RAM...")
    from app.embeddings.model import get_embedder
    embedder = get_embedder()
    # Forzar una inferencia dummy para que el modelo quede caliente
    embedder.embed_text("inicialización del sistema")
    logger.info(" Modelo de embeddings listo en RAM")

    logger.info("Verificando conexión a Qdrant...")
    from app.vectorstore.qdrant_client import get_qdrant_manager
    qdrant = get_qdrant_manager()
    logger.info("Qdrant conectado")

    logger.info("Verificando Ollama...")
    from app.llm.client import OllamaClient
    ollama = OllamaClient()
    if ollama.is_available():
        logger.info("Ollama disponible")
    else:
        logger.warning(" Ollama no disponible — verifica que está corriendo")

    logger.info(f"Modelo LLM     : {settings.OLLAMA_MODEL}")
    logger.info(f"Embedding model: {settings.EMBEDDING_MODEL_NAME}")
    logger.info(f"Chunk size     : {settings.CHUNK_SIZE} | Overlap: {settings.CHUNK_OVERLAP}")
    logger.info(f"Top-K          : {settings.TOP_K}")
    logger.info("Sistema listo para recibir requests")

    yield

    # ── Al apagar ──
    logger.info("Apagando el sistema RAG...")


# ─── Crear la aplicación FastAPI ──────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Sistema RAG con Base de Datos Vectorial

    Sistema de Retrieval-Augmented Generation que permite:
    - **Ingestar** documentos PDF y texto
    - **Consultar** en lenguaje natural con respuestas fieles al documento
    - **Evaluar** la calidad con métricas RAGAS

    ### Flujo
    1. POST `/ingest` — Sube tus documentos
    2. POST `/query` — Haz preguntas
    3. POST `/evaluate` — Mide la calidad
    """,
    lifespan=lifespan
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
# Permite que frontends (React, Vue, etc.) consuman la API sin bloqueos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Registrar rutas ──────────────────────────────────────────────────────────
app.include_router(router, prefix="/api/v1")


# ─── Ruta raíz ────────────────────────────────────────────────────────────────
@app.get("/", tags=["Sistema"])
async def root():
    return {
        "system": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "api": "/api/v1"
    }