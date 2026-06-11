from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    HnswConfigDiff,
    OptimizersConfigDiff,
)

from app.core.chunks import ensure_chunk_id, validate_indexed_chunk
from app.core.config import settings
from app.core.logger import logger
from app.vectorstore.base import BaseVectorStoreProvider


class QdrantVectorStoreProvider(BaseVectorStoreProvider):
    def __init__(self):
        logger.info(f"Conectando a Qdrant en {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
        )
        logger.info("Conexión a Qdrant establecida")

    def create_collection(self, recreate: bool = False, vector_size: int | None = None):
        collection_name = settings.QDRANT_COLLECTION_NAME
        resolved_size = vector_size or settings.EMBEDDING_DIMENSION

        if resolved_size != settings.EMBEDDING_DIMENSION:
            logger.warning(
                "Dimensión del provider (%s) difiere de EMBEDDING_DIMENSION en config (%s). "
                "Usando dimensión del provider.",
                resolved_size,
                settings.EMBEDDING_DIMENSION,
            )

        existing = [collection.name for collection in self.client.get_collections().collections]

        if collection_name in existing:
            current_size = self._get_collection_vector_size(collection_name)
            if current_size != resolved_size:
                raise ValueError(
                    f"La colección '{collection_name}' usa dimensión {current_size}, "
                    f"pero el provider requiere {resolved_size}. "
                    "Usa recreate_collection=true para recrearla."
                )

            if recreate:
                logger.warning(f"Eliminando colección existente: {collection_name}")
                self.client.delete_collection(collection_name)
            else:
                logger.info(f"Colección ya existe: {collection_name} | dimensión={current_size}")
                return

        logger.info(f"Creando colección con HNSW optimizado: {collection_name} | dimensión={resolved_size}")
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=resolved_size,
                distance=Distance.COSINE,
                on_disk=False,
            ),
            hnsw_config=HnswConfigDiff(
                m=16,
                ef_construct=64,
                full_scan_threshold=10,
            ),
            optimizers_config=OptimizersConfigDiff(
                indexing_threshold=0,
            ),
        )
        logger.info("Colección con HNSW optimizado creada con éxito")

    def insert_points(self, chunks: list[dict]) -> int:
        """
        Inserta chunks con embeddings en Qdrant.
        Cada punto usa un ID estable derivado del contenido y metadata del chunk.
        """
        if not chunks:
            logger.warning("insert_points llamado sin chunks")
            return 0

        vector_size = self._get_collection_vector_size(settings.QDRANT_COLLECTION_NAME)
        points = []

        for index, chunk in enumerate(chunks):
            validate_indexed_chunk(chunk, index, vector_size)
            chunk_id = ensure_chunk_id(chunk)
            metadata = dict(chunk.get("metadata", {}))

            points.append(
                PointStruct(
                    id=chunk_id,
                    vector=chunk["embedding"],
                    payload={
                        "text": chunk["text"],
                        "metadata": metadata,
                    },
                )
            )

        batch_size = 100
        for start in range(0, len(points), batch_size):
            batch = points[start : start + batch_size]
            self.client.upsert(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points=batch,
            )
            logger.debug(f"Insertados {min(start + batch_size, len(points))}/{len(points)} puntos")

        logger.info(f"Total puntos insertados en Qdrant: {len(points)}")
        return len(points)

    def search(self, query_vector: list[float], top_k: int = None) -> list[dict]:
        """Busca los chunks más similares al vector de la consulta."""
        if not query_vector:
            raise ValueError("El vector de consulta no puede estar vacío.")

        expected_size = self._get_collection_vector_size(settings.QDRANT_COLLECTION_NAME)
        if len(query_vector) != expected_size:
            raise ValueError(
                f"Dimensión del query vector ({len(query_vector)}) != dimensión de la colección ({expected_size})."
            )

        k = top_k or settings.TOP_K

        results = self.client.search(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query_vector=query_vector,
            limit=k,
            with_payload=True,
        )

        normalized_results = []
        for result in results:
            payload = result.payload or {}
            metadata = dict(payload.get("metadata") or {})

            # Compatibilidad de lectura para puntos indexados antes de normalizar metadata.
            for key in ("filename", "file_path", "file_type", "chunk_index", "char_count", "chunk_id"):
                if key in payload and key not in metadata:
                    metadata[key] = payload[key]

            normalized_results.append(
                {
                    "text": payload.get("text", ""),
                    "metadata": metadata,
                    "score": result.score,
                }
            )

        return normalized_results

    def get_collection_info(self) -> dict:
        """Retorna estadísticas de la colección."""
        info = self.client.get_collection(settings.QDRANT_COLLECTION_NAME)
        return {
            "name": settings.QDRANT_COLLECTION_NAME,
            "total_points": info.points_count,
            "vector_size": self._get_collection_vector_size(settings.QDRANT_COLLECTION_NAME),
            "status": str(info.status),
        }

    def _get_collection_vector_size(self, collection_name: str) -> int:
        info = self.client.get_collection(collection_name)
        vectors = info.config.params.vectors

        if hasattr(vectors, "size"):
            return vectors.size

        if isinstance(vectors, dict):
            first_vector = next(iter(vectors.values()))
            return first_vector.size

        raise ValueError(f"No se pudo determinar la dimensión de la colección '{collection_name}'.")
