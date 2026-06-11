import json
from pathlib import Path

from app.core.config import settings
from app.core.logger import logger
from app.ingestion.loaders.base import BaseLoader
from app.ingestion.loaders.file_loader import FileLoader
from app.ingestion.processors.cleaner import TextCleaner
from app.ingestion.processors.chunker import TextChunker


class IngestionPipeline:
    def __init__(
        self,
        loader: BaseLoader | None = None,
        cleaner: TextCleaner | None = None,
        chunker: TextChunker | None = None,
    ):
        self.loader = loader
        self.cleaner = cleaner or TextCleaner()
        self.chunker = chunker or TextChunker()

    def run(self, source_path: str | None = None) -> list[dict]:
        """
        Ejecuta el pipeline completo:
        fuente → texto → limpieza → chunks
        """
        loader = self._resolve_loader(source_path)
        logger.info(f"Iniciando pipeline de ingesta con loader: {loader.__class__.__name__}")

        # Paso 1: Cargar documentos
        documents = loader.load()

        logger.info(f"Documentos cargados: {len(documents)}")
        return self.run_documents(documents)

    def run_documents(self, documents: list[dict], save_chunks: bool = True) -> list[dict]:
        """Limpia y fragmenta documentos ya cargados (archivos, Supabase, webhook, etc.)."""
        all_chunks = []

        for doc in documents:
            self._validate_document(doc)

            clean_text = self.cleaner.clean(doc["text"])
            metadata = dict(doc.get("metadata", {}))
            metadata["clean_char_count"] = len(clean_text)

            chunks = self.chunker.chunk(clean_text, metadata)
            all_chunks.extend(chunks)

        logger.info(f"Total chunks generados: {len(all_chunks)}")

        if save_chunks and all_chunks:
            self._save_chunks(all_chunks)

        return all_chunks

    def _resolve_loader(self, source_path: str | None) -> BaseLoader:
        if source_path:
            return FileLoader(source_path)

        if self.loader:
            return self.loader

        raise ValueError("Debes proporcionar un source_path o inicializar el pipeline con un BaseLoader.")

    def _validate_document(self, document: dict):
        if "text" not in document:
            raise ValueError("Documento inválido: falta la clave 'text'.")

        if "metadata" not in document or not isinstance(document["metadata"], dict):
            raise ValueError("Documento inválido: falta la clave 'metadata' como diccionario.")

    def _save_chunks(self, chunks: list[dict]):
        """Guarda los chunks en disco como respaldo."""
        output_path = Path(settings.CHUNKS_DATA_PATH) / "chunks.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        logger.info(f"Chunks guardados en: {output_path}")
