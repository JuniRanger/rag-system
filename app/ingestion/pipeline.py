import json
from pathlib import Path
from app.ingestion.loader import DocumentLoader
from app.ingestion.cleaner import TextCleaner
from app.ingestion.chunker import TextChunker
from app.core.config import settings
from app.core.logger import logger

class IngestionPipeline:
    def __init__(self):
        self.loader = DocumentLoader()
        self.cleaner = TextCleaner()
        self.chunker = TextChunker()

    def run(self, source_path: str) -> list[dict]:
        """
        Ejecuta el pipeline completo:
        archivo(s) → texto → limpieza → chunks
        """
        logger.info(f"Iniciando pipeline de ingesta desde: {source_path}")

        # Paso 1: Cargar documentos
        path = Path(source_path)
        if path.is_dir():
            documents = self.loader.load_directory(source_path)
        else:
            documents = [self.loader.load_file(source_path)]

        logger.info(f"Documentos cargados: {len(documents)}")

        # Paso 2: Limpiar y fragmentar cada documento
        all_chunks = []
        for doc in documents:
            clean_text = self.cleaner.clean(doc["text"])

            metadata = {
                "filename": doc["filename"],
                "file_path": doc["file_path"],
                "file_type": doc["file_type"],
            }

            chunks = self.chunker.chunk(clean_text, metadata)
            all_chunks.extend(chunks)

        logger.info(f"Total chunks generados: {len(all_chunks)}")

        # Paso 3: Guardar chunks en disco para referencia
        self._save_chunks(all_chunks)

        return all_chunks

    def _save_chunks(self, chunks: list[dict]):
        """Guarda los chunks en disco como respaldo."""
        output_path = Path(settings.CHUNKS_DATA_PATH) / "chunks.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        logger.info(f"Chunks guardados en: {output_path}")