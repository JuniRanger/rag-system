"""
Script para reconstruir el índice vectorial desde los chunks guardados en disco.
Útil cuando Qdrant se reinició y perdió los datos pero los chunks ya existen.

Uso:
    python scripts/build_index.py
    python scripts/build_index.py --recreate
"""
import sys
import json
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.vectorstore.indexer import VectorIndexer
from app.core.config import settings
from app.core.logger import logger


def main():
    parser = argparse.ArgumentParser(description="Reconstruir índice vectorial desde chunks en disco")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Eliminar y recrear la colección desde cero"
    )
    parser.add_argument(
        "--chunks-path",
        type=str,
        default="data/chunks/chunks.json",
        help="Ruta al archivo de chunks guardado"
    )
    args = parser.parse_args()

    chunks_path = Path(args.chunks_path)

    # Verificar que existen los chunks en disco
    if not chunks_path.exists():
        logger.error(f"No se encontraron chunks en: {chunks_path}")
        logger.error("Primero ejecuta: python scripts/ingest.py --source data/raw")
        sys.exit(1)

    # Cargar chunks desde disco
    logger.info(f"Cargando chunks desde: {chunks_path}")
    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    logger.info(f"Chunks cargados: {len(chunks)}")

    # Reconstruir índice
    logger.info("Reconstruyendo índice en Qdrant...")
    indexer = VectorIndexer()
    info = indexer.index_chunks(chunks, recreate=args.recreate)

    logger.info(f"=== Índice reconstruido ===")
    logger.info(f"Colección: {info}")
    print(f"\n✅ Índice reconstruido: {len(chunks)} chunks en Qdrant")


if __name__ == "__main__":
    main()