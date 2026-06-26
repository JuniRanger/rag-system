import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.core.config import settings
from app.core.logger import logger
from app.core.providers import get_embedding_provider, get_vector_store_provider
from app.core.supabase import get_supabase_client, require_supabase_config
from app.ingestion.loaders.supabase_loader import SupabaseLoader
from app.ingestion.pipeline import IngestionPipeline
from app.vectorstore.indexer import VectorIndexer

SyncMode = Literal["full", "incremental"]


class SupabaseSyncService:
    def __init__(self):
        require_supabase_config()
        self.client = get_supabase_client()
        self.table = settings.SUPABASE_TABLE

    def sync(
        self,
        *,
        table: str | None = None,
        mode: SyncMode = "incremental",
        recreate_collection: bool = False,
    ) -> dict:
        loader = self._build_loader(table)
        state = self._load_state(loader.table)

        if mode == "full":
            documents, last_cursor = loader.fetch_all()
            save_chunks = True
        else:
            documents, last_cursor = loader.load_since(state.get("last_cursor"))
            save_chunks = False

        result = self._ingest_documents(
            loader=loader,
            documents=documents,
            last_cursor=last_cursor,
            recreate_collection=recreate_collection,
            save_chunks=save_chunks,
        )
        result["mode"] = mode
        return result

    def ingest_webhook_record(self, payload: dict) -> dict:
        event_type = payload.get("type", "").upper()
        table = payload.get("table") or self.table
        record = payload.get("record")

        if event_type != "INSERT":
            return {
                "success": True,
                "message": f"Evento {event_type} ignorado; solo se procesan INSERT.",
                "record_id": None,
                "chunks_created": 0,
            }

        if table != settings.SUPABASE_TABLE:
            return {
                "success": True,
                "message": f"Tabla '{table}' ignorada; webhook configurado para '{settings.SUPABASE_TABLE}'.",
                "record_id": None,
                "chunks_created": 0,
            }

        if not record:
            raise ValueError("El webhook no incluyó el campo 'record'.")

        loader = self._build_loader(table)
        document = loader.row_to_document(record)
        last_cursor = loader.extract_cursor_value(record)

        result = self._ingest_documents(
            loader=loader,
            documents=[document],
            last_cursor=last_cursor,
            recreate_collection=False,
            save_chunks=False,
        )

        return {
            "success": True,
            "message": "Registro indexado desde webhook.",
            "record_id": document["metadata"].get("record_id"),
            "chunks_created": result["chunks_created"],
            "collection_info": result["collection_info"],
        }

    def _ingest_documents(
        self,
        *,
        loader: SupabaseLoader,
        documents: list[dict],
        last_cursor: Any | None,
        recreate_collection: bool,
        save_chunks: bool,
    ) -> dict:
        if not documents:
            logger.info("No hay documentos nuevos para indexar")
            collection_info = VectorIndexer().get_index_stats()
            return {
                "success": True,
                "message": "No hay registros nuevos para indexar.",
                "table": loader.table,
                "records_processed": 0,
                "chunks_created": 0,
                "collection_info": collection_info,
                "sync_state": self._load_state(loader.table),
            }

        pipeline = IngestionPipeline()
        chunks = pipeline.run_documents(documents, save_chunks=save_chunks)

        indexer = VectorIndexer(
            embedding_provider=get_embedding_provider(),
            vector_store_provider=get_vector_store_provider(),
        )
        collection_info = indexer.index_chunks(chunks, recreate=recreate_collection)

        if last_cursor is not None:
            self._save_state(loader.table, last_cursor)

        return {
            "success": True,
            "message": "Sincronización completada.",
            "table": loader.table,
            "records_processed": len(documents),
            "chunks_created": len(chunks),
            "collection_info": collection_info,
            "sync_state": self._load_state(loader.table),
        }

    def _build_loader(self, table: str | None = None) -> SupabaseLoader:
        resolved_table = table or settings.SUPABASE_TABLE
        return SupabaseLoader(self.client, resolved_table)

    def _state_path(self, table: str) -> Path:
        return Path(settings.PROCESSED_DATA_PATH) / f"supabase_sync_{table}.json"

    def _load_state(self, table: str) -> dict:
        path = self._state_path(table)
        if not path.exists():
            return {"table": table, "last_cursor": None, "last_synced_at": None}

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    def _save_state(self, table: str, last_cursor: Any):
        state = {
            "table": table,
            "last_cursor": last_cursor,
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
        }

        path = self._state_path(table)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False, indent=2, default=str)

        logger.info(f"Cursor de sync actualizado: {state}")
