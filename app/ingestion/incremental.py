"""Ingesta incremental: un registro Supabase -> embedding -> upsert Qdrant."""
import asyncio
import uuid
from typing import Any

from qdrant_client.models import PointStruct

from app.core.config import settings
from app.core.logger import logger
from app.embeddings.model import get_embedder
from app.embeddings.ollama_embedder import OllamaEmbedder, OllamaEmbeddingError
from app.vectorstore.qdrant_client import get_qdrant_manager


class IncrementalIngestError(Exception):
    """Error de negocio en ingesta incremental."""


def _qdrant_point_id(record_id: Any) -> str | int:
    """Qdrant acepta int o UUID string; otros ids se mapean a UUID determinista."""
    if isinstance(record_id, int):
        return record_id
    raw = str(record_id).strip()
    try:
        uuid.UUID(raw)
        return raw
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, raw))


def extract_record_fields(record: dict[str, Any]) -> tuple[str | int, str]:
    """ID y texto desde record segun campos configurados en .env."""
    if settings.SUPABASE_RECORD_ID_FIELD not in record:
        raise IncrementalIngestError(
            f"Falta campo id '{settings.SUPABASE_RECORD_ID_FIELD}' en record"
        )

    record_id = record[settings.SUPABASE_RECORD_ID_FIELD]
    text: str | None = None
    for field in settings.supabase_text_field_candidates():
        if field in record and record[field] is not None:
            candidate = str(record[field]).strip()
            if candidate:
                text = candidate
                break

    if not text:
        raise IncrementalIngestError(
            f"Sin texto en record (campos probados: {settings.supabase_text_field_candidates()})"
        )

    return record_id, text


class IncrementalIngestService:
    def __init__(self) -> None:
        self._ollama_embedder: OllamaEmbedder | None = None
        self.qdrant = get_qdrant_manager()

    def _use_ollama(self) -> bool:
        return settings.INCREMENTAL_EMBEDDING_BACKEND.strip().lower() == "ollama"

    async def _embed(self, text: str) -> list[float]:
        if self._use_ollama():
            if self._ollama_embedder is None:
                self._ollama_embedder = OllamaEmbedder()
            return await self._ollama_embedder.embed_text(text)
        # Mismo espacio vectorial que ingesta masiva (384d por defecto)
        return await asyncio.to_thread(get_embedder().embed_text, text)

    async def ingest_record(
        self,
        *,
        table: str,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        allowed = settings.supabase_allowed_tables()
        if allowed and table not in allowed:
            return {
                "skipped": True,
                "reason": f"tabla '{table}' no permitida",
            }

        record_id, text = extract_record_fields(record)
        point_id = _qdrant_point_id(record_id)

        try:
            vector = await self._embed(text)
        except OllamaEmbeddingError as exc:
            raise IncrementalIngestError(str(exc)) from exc

        # Coleccion lista + upsert de un solo punto
        self.qdrant.create_collection(recreate=False)
        payload = {
            "text": text,
            "filename": f"supabase:{table}",
            "file_path": "",
            "file_type": ".supabase",
            "chunk_index": 0,
            "char_count": len(text),
            "source": "supabase",
            "supabase_id": str(record_id),
            "supabase_table": table,
        }
        point = PointStruct(id=point_id, vector=vector, payload=payload)
        self.qdrant.upsert_points([point])

        logger.info(
            f"Ingesta incremental OK | table={table} id={record_id} point_id={point_id}"
        )
        return {
            "skipped": False,
            "point_id": str(point_id),
            "supabase_id": str(record_id),
            "table": table,
            "text_length": len(text),
            "vector_dimension": len(vector),
        }
