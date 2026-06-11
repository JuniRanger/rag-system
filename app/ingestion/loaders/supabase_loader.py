from typing import TYPE_CHECKING, Any

from app.core.config import settings
from app.core.logger import logger
from app.ingestion.loaders.base import BaseLoader

if TYPE_CHECKING:
    from supabase import Client

DEFAULT_PAGE_SIZE = 500


class SupabaseLoader(BaseLoader):
    def __init__(
        self,
        client: "Client | Any",
        table: str,
        *,
        id_column: str | None = None,
        cursor_column: str | None = None,
        text_columns: list[str] | None = None,
        page_size: int = DEFAULT_PAGE_SIZE,
    ):
        self.client = client
        self.table = table
        self.id_column = id_column or settings.SUPABASE_ID_COLUMN
        self.cursor_column = cursor_column or settings.SUPABASE_CURSOR_COLUMN
        self.text_columns = text_columns if text_columns is not None else self._parse_text_columns()
        if not self.text_columns:
            raise ValueError(
                "SUPABASE_TEXT_COLUMNS debe definir al menos una columna a indexar "
                "(separadas por coma en .env)."
            )
        self.page_size = page_size

    def load(self) -> list[dict]:
        """Carga todos los registros de la tabla con paginación."""
        documents, _ = self.fetch_all()
        return documents

    def fetch_all(self) -> tuple[list[dict], Any | None]:
        logger.info(f"Cargando todos los documentos de la tabla {self.table}")
        return self._load_rows()

    def load_since(self, cursor_value: Any | None) -> tuple[list[dict], Any | None]:
        """
        Carga registros con cursor > cursor_value.
        Si cursor_value es None, equivale a load().
        """
        if cursor_value is None:
            logger.info(f"Sin cursor previo — cargando tabla completa: {self.table}")
            return self.fetch_all()

        logger.info(
            f"Cargando documentos de {self.table} con {self.cursor_column} > {cursor_value}"
        )
        return self._load_rows(cursor_value=cursor_value)

    def load_record(self, record_id: Any) -> dict:
        response = (
            self.client.table(self.table)
            .select("*")
            .eq(self.id_column, record_id)
            .single()
            .execute()
        )
        row = response.data
        if not row:
            raise ValueError(f"No se encontró el registro {self.id_column}={record_id}")
        return self.row_to_document(row)

    def row_to_document(self, row: dict) -> dict:
        text = self.build_text(row)
        record_id = row.get(self.id_column)

        return {
            "text": text,
            "metadata": {
                "source": "supabase",
                "table": self.table,
                "record_id": record_id,
            },
        }

    def build_text(self, row: dict) -> str:
        """Convierte un registro en texto indexable usando solo SUPABASE_TEXT_COLUMNS."""
        parts = []
        for column in self.text_columns:
            value = row.get(column)
            if value is None or value == "":
                continue
            parts.append(f"{column}: {value}")
        text = "\n".join(parts)

        if not text.strip():
            raise ValueError(
                f"El registro {row.get(self.id_column)} no produjo texto indexable."
            )

        return text

    def extract_cursor_value(self, row: dict) -> Any:
        if self.cursor_column not in row:
            raise ValueError(
                f"La columna de cursor '{self.cursor_column}' no existe en el registro."
            )
        return row[self.cursor_column]

    def _parse_text_columns(self) -> list[str]:
        raw = settings.SUPABASE_TEXT_COLUMNS.strip()
        if not raw:
            return []
        return [column.strip() for column in raw.split(",") if column.strip()]

    def _load_rows(self, cursor_value: Any | None = None) -> tuple[list[dict], Any | None]:
        documents = []
        last_cursor = None
        offset = 0

        while True:
            query = self.client.table(self.table).select("*")

            if cursor_value is not None:
                query = query.gt(self.cursor_column, cursor_value)

            query = query.order(self.cursor_column).range(offset, offset + self.page_size - 1)
            response = query.execute()
            rows = response.data or []

            if not rows:
                break

            for row in rows:
                documents.append(self.row_to_document(row))
                last_cursor = self.extract_cursor_value(row)

            if len(rows) < self.page_size:
                break

            offset += self.page_size

        logger.info(f"Documentos cargados desde Supabase: {len(documents)}")
        return documents, last_cursor
