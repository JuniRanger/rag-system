from pathlib import Path
from pypdf import PdfReader

from app.ingestion.loaders.base import BaseLoader
from app.core.logger import logger


class FileLoader(BaseLoader):

    SUPPORTED_EXTENSIONS = {
        ".pdf",
        ".txt",
        ".md",
        ".docx",
        ".pptx",
        ".csv",
        ".xlsx"
    }

    def __init__(self, source_path: str):
        self.source_path = Path(source_path)

    def load(self) -> list[dict]:
        """
        Punto de entrada estándar del loader.
        """

        if self.source_path.is_dir():
            return self._load_directory()

        return [self._load_file(self.source_path)]

    def _load_file(self, path: Path) -> dict:

        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {path}")

        if path.suffix not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Formato no soportado: {path.suffix}")

        logger.info(f"Cargando archivo: {path.name}")

        if path.suffix == ".pdf":
            text = self._load_pdf(path)
        else:
            text = self._load_text(path)

        return {
            "text": text,
            "metadata": {
                "source": "file",
                "filename": path.name,
                "file_path": str(path),
                "file_type": path.suffix,
                "char_count": len(text),
            }
        }

    def _load_pdf(self, path: Path) -> str:

        reader = PdfReader(str(path))

        pages = []

        for i, page in enumerate(reader.pages):

            text = page.extract_text()

            if text and text.strip():

                pages.append(text)

                logger.debug(
                    f"Página {i+1} extraída: {len(text)} caracteres"
                )

        return "\n\n".join(pages)

    def _load_text(self, path: Path) -> str:

        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_directory(self) -> list[dict]:

        documents = []

        for file_path in self.source_path.rglob("*"):

            if file_path.suffix not in self.SUPPORTED_EXTENSIONS:
                continue

            try:
                documents.append(
                    self._load_file(file_path)
                )

            except Exception as e:

                logger.error(
                    f"Error cargando {file_path.name}: {e}"
                )

        logger.info(
            f"Total documentos cargados: {len(documents)}"
        )

        return documents