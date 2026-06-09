"""Consultas sync a documentos_tecnicos en Supabase (para function calling)."""
from typing import Any

import httpx

from app.core.config import settings
from app.core.logger import logger
from app.ingestion.documento_tecnico import documento_tecnico_to_text
from app.ingestion.supabase_sync import _rest_headers, _service_key


def is_configured() -> bool:
    return bool((settings.SUPABASE_URL or "").strip() and _service_key())


def _table_name() -> str:
    return (settings.SUPABASE_SYNC_TABLE or "documentos_tecnicos").strip()


def _ilike(value: str) -> str:
    return f"ilike.*{value.strip()}*"


def fetch_documentos_tecnicos(
    *,
    marca: str | None = None,
    modelo: str | None = None,
    texto: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """
    Lee filas de documentos_tecnicos via PostgREST (sync, para tools).
    `texto` busca en problema, diagnostico y categoria_problema.
    """
    if not is_configured():
        return []

    base_url = settings.SUPABASE_URL.rstrip("/")
    table = _table_name()
    url = f"{base_url}/rest/v1/{table}"
    headers = _rest_headers(settings.SUPABASE_SCHEMA)
    params: dict[str, str] = {"select": "*", "limit": str(limit)}

    if marca and marca.strip():
        params["vehiculo_marca"] = _ilike(marca)
    if modelo and modelo.strip():
        params["vehiculo_modelo"] = _ilike(modelo)
    if texto and texto.strip():
        term = texto.strip()
        params["or"] = (
            f"(problema.ilike.*{term}*,"
            f"diagnostico.ilike.*{term}*,"
            f"categoria_problema.ilike.*{term}*)"
        )

    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(url, headers=headers, params=params)
            if response.status_code >= 400:
                logger.warning(
                    "[TOOLS_SUPABASE] GET %s status=%s body=%s",
                    response.url,
                    response.status_code,
                    response.text[:300],
                )
                return []
            rows = response.json()
    except httpx.HTTPError as exc:
        logger.warning(f"[TOOLS_SUPABASE] Error REST: {exc}")
        return []

    return rows if isinstance(rows, list) else []


def format_documento_row(row: dict[str, Any]) -> str:
    """Texto legible para devolver al LLM desde una fila Supabase."""
    body = documento_tecnico_to_text(row)
    fuente = f"supabase:{settings.SUPABASE_SCHEMA}:{_table_name()}"
    return f"Fuente: {fuente}\n{body}"


def split_car_name(car_name: str) -> tuple[str | None, str | None]:
    """Heuristica: 'Chevrolet Pop 2005' -> marca Chevrolet, modelo Pop 2005."""
    parts = car_name.strip().split(None, 1)
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]
