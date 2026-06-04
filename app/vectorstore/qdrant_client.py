from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    HnswConfigDiff,  
    OptimizersConfigDiff 
)
from functools import lru_cache
from app.core.config import settings
from app.core.logger import logger

class QdrantManager:
    def __init__(self):
        logger.info(f"Conectando a Qdrant en {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        logger.info("Conexión a Qdrant establecida")

    # ── MÉTODOS DE LA CLASE (Todos llevan un tabulador/4 espacios adentro) ──

    def create_collection(self, recreate: bool = False):
        collection_name = settings.QDRANT_COLLECTION_NAME
        existing = [c.name for c in self.client.get_collections().collections]

        if collection_name in existing:
            if recreate:
                logger.warning(f"Eliminando colección existente: {collection_name}")
                self.client.delete_collection(collection_name)
            else:
                logger.info(f"Colección ya existe: {collection_name}")
                return

        logger.info(f"Creando colección con HNSW optimizado: {collection_name}")
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIMENSION,
                distance=Distance.COSINE,
                on_disk=False  # Mantener estrictamente en RAM para máxima velocidad
            ),
            hnsw_config=HnswConfigDiff(
                m=16,               # Conexiones estándar por nodo [balance recall/velocidad]
                ef_construct=64,    # Bajamos ligeramente de 100 a 64 para agilizar consultas locales
                full_scan_threshold=10  #  CRÍTICO: 0 fuerza el uso de HNSW ignorando la fuerza bruta
            ),
            optimizers_config=OptimizersConfigDiff(
                indexing_threshold=0  # Indexación en tiempo real inmediata
            )
        )
        logger.info("Colección con HNSW optimizado creada con éxito")

    def insert_points(self, chunks: list[dict]):
        """
        Inserta los chunks con sus vectores en Qdrant.
        Cada punto tiene: ID único, vector, y payload (metadatos).
        """
        points = []
        for i, chunk in enumerate(chunks):
            point = PointStruct(
                id=i,
                vector=chunk["embedding"],
                payload={
                    "text": chunk["text"],
                    "filename": chunk.get("filename", ""),
                    "file_path": chunk.get("file_path", ""),
                    "file_type": chunk.get("file_type", ""),
                    "chunk_index": chunk.get("chunk_index", i),
                    "char_count": chunk.get("char_count", 0),
                }
            )
            points.append(point)

        # Insertar en lotes de 100 para no saturar la conexión
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points=batch
            )
            logger.debug(f"Insertados {min(i+batch_size, len(points))}/{len(points)} puntos")

        logger.info(f"Total puntos insertados en Qdrant: {len(points)}")

    def upsert_points(self, points: list[PointStruct]) -> None:
        """Upsert de uno o mas puntos (ingesta incremental / webhooks)."""
        if not points:
            return
        self.client.upsert(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points=points,
        )
        logger.info(f"Upsert en Qdrant: {len(points)} punto(s)")

    def search(self, query_vector: list[float], top_k: int = None) -> list[dict]:
        """
        Busca los chunks más similares al vector de la consulta.
        Retorna los top_k resultados con su score de similitud.
        """
        k = top_k or settings.TOP_K

        results = self.client.search(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query_vector=query_vector,
            limit=k,
            with_payload=True  # Incluye el texto y metadatos en la respuesta
        )

        return [
            {
                "text": r.payload["text"],
                "filename": r.payload.get("filename", ""),
                "chunk_index": r.payload.get("chunk_index", 0),
                "score": r.score  # Score de similitud coseno (0 a 1)
            }
            for r in results
        ]

    def get_collection_info(self) -> dict:
        """Retorna estadísticas de la colección — útil para debugging."""
        info = self.client.get_collection(settings.QDRANT_COLLECTION_NAME)
        return {
            "name": settings.QDRANT_COLLECTION_NAME,
            "total_points": info.points_count,
            "status": str(info.status)
        }

# ── FUNCIONES DE AYUDA (Fuera de la clase) ──

@lru_cache()
def get_qdrant_manager() -> QdrantManager:
    return QdrantManager()