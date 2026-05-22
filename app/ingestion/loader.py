import os
from pathlib import Path
from pypdf import PdfReader
from app.core.logger import logger

class DocumentLoader:
    SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx", ".pptx", ".csv", ".xlsx"}

    def load_file(self, file_path: str) -> dict:
        """Carga un archivo y retorna su texto y metadatos."""
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        if path.suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Formato no soportado: {path.suffix}")

        logger.info(f"Cargando archivo: {path.name}")

        if path.suffix == ".pdf":
            text = self._load_pdf(path)
        else:
            text = self._load_text(path)

        return {
            "text": text,
            "filename": path.name,
            "file_path": str(path),
            "file_type": path.suffix,
            "char_count": len(text)
        }

    def _load_pdf(self, path: Path) -> str:
        reader = PdfReader(str(path))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                pages.append(text)
                logger.debug(f"  Página {i+1} extraída: {len(text)} caracteres")
        return "\n\n".join(pages)

    def _load_text(self, path: Path) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def load_directory(self, directory: str) -> list[dict]:
        """Carga todos los documentos soportados de una carpeta."""
        dir_path = Path(directory)
        documents = []

        for file_path in dir_path.rglob("*"):
            if file_path.suffix in self.SUPPORTED_EXTENSIONS:
                try:
                    doc = self.load_file(str(file_path))
                    documents.append(doc)
                except Exception as e:
                    logger.error(f"Error cargando {file_path.name}: {e}")

        logger.info(f"Total documentos cargados: {len(documents)}")
        return documents
