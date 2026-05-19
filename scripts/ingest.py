"""
Script para ingestar documentos al sistema RAG.

Uso:
    python scripts/ingest.py --source data/raw
    python scripts/ingest.py --source data/raw/mi_documento.pdf
    python scripts/ingest.py --source data/raw --recreate
"""
import sys
import argparse
from pathlib import Path

# Agregar el directorio raíz al path para poder importar app/
sys.path.append(str(Path(__file__).parent.parent))

from app.ingestion.pipeline import IngestionPipeline
from app.vectorstore.indexer import VectorIndexer
from app.core.logger import logger


def main():
    parser = argparse.ArgumentParser(description="Ingestar documentos al sistema RAG")
    parser.add_argument(
        "--source",
        type=str,
        default="data/raw",
        help="Ruta al archivo o carpeta a ingestar"
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Eliminar y recrear la colección desde cero"
    )
    args = parser.parse_args()

    logger.info(f"=== Iniciando ingesta desde: {args.source} ===")

    # Verificar que la fuente existe
    source_path = Path(args.source)
    if not source_path.exists():
        logger.error(f"La ruta no existe: {args.source}")
        sys.exit(1)

    # Paso 1: Pipeline de ingesta
    logger.info("Paso 1/2: Cargando, limpiando y fragmentando documentos...")
    ingestion = IngestionPipeline()
    chunks = ingestion.run(args.source)

    if not chunks:
        logger.error("No se generaron chunks. Verifica que los documentos tienen contenido.")
        sys.exit(1)

    logger.info(f"Chunks generados: {len(chunks)}")

    # Paso 2: Indexar en Qdrant
    logger.info("Paso 2/2: Generando embeddings e indexando en Qdrant...")
    indexer = VectorIndexer()
    info = indexer.index_chunks(chunks, recreate=args.recreate)

    logger.info(f"=== Ingesta completada ===")
    logger.info(f"Colección: {info}")
    print(f"\n✅ Ingesta exitosa: {len(chunks)} chunks indexados en Qdrant")


if __name__ == "__main__":
    main()