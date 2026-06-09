"""Sincroniza filas de Supabase -> Qdrant (fallback si el webhook no llego)."""
from typing import Any

import httpx

from app.core.config import settings
from app.core.logger import logger
from app.ingestion.incremental import IncrementalIngestService, IncrementalIngestError


class SupabaseSyncError(Exception):
    pass


def _service_key() -> str:
    key = (settings.SUPABASE_SERVICE_KEY or "").strip()
    if key.lower().startswith("bearer "):
        return key.split(" ", 1)[1].strip()
    return key


def _normalize_schema(schema: str | None = None) -> str:
    return (schema or settings.SUPABASE_SCHEMA or "public").strip() or "public"


def _rest_headers(schema: str | None = None) -> dict[str, str]:
    """
    Headers para PostgREST.

    - Accept: application/json -> respuesta como array (NO object+json).
    - Accept-Profile / Content-Profile solo si el schema NO es public.
      Enviar Accept-Profile: rag cuando rag no esta expuesto -> 406 PGRST106.
    """
    api_key = _service_key()
    schema_name = _normalize_schema(schema)
    headers: dict[str, str] = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }
    if schema_name.lower() != "public":
        headers["Accept-Profile"] = schema_name
        headers["Content-Profile"] = schema_name
    return headers


def _log_supabase_debug(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    params: dict[str, str] | None,
    response: httpx.Response,
) -> None:
    """Logs temporales de debugging para diagnosticar 406/403 en Supabase REST."""
    safe_headers = {
        key: ("***" if key.lower() in {"apikey", "authorization"} else value)
        for key, value in headers.items()
    }
    logger.warning(
        "[SUPABASE_DEBUG] %s %s | params=%s | headers=%s | status=%s | body=%s",
        method,
        url,
        params,
        safe_headers,
        response.status_code,
        response.text,
    )


def _raise_for_supabase_response(
    response: httpx.Response,
    *,
    schema_name: str,
    table_name: str,
) -> None:
    if response.status_code == 406:
        raise SupabaseSyncError(
            f"Schema '{schema_name}' no expuesto en PostgREST (406). "
            f"Respuesta: {response.text}. "
            "Usa SUPABASE_SCHEMA=public o agrega el schema en "
            "Supabase Dashboard -> Settings -> API -> Exposed schemas."
        )
    if response.status_code == 403:
        raise SupabaseSyncError(
            f"Permiso denegado en {schema_name}.{table_name} (403). "
            f"Respuesta: {response.text}. "
            f"Ejecuta en SQL: GRANT SELECT ON {schema_name}.{table_name} TO service_role;"
        )
    if response.status_code == 404:
        return
    response.raise_for_status()


async def list_supabase_tables(schema: str | None = None) -> list[str]:
    """Tablas expuestas en PostgREST para el schema indicado."""
    base_url = (settings.SUPABASE_URL or "").rstrip("/")
    if not base_url or not _service_key():
        raise SupabaseSyncError("Configura SUPABASE_URL y SUPABASE_SERVICE_KEY")

    schema_name = _normalize_schema(schema)
    headers = _rest_headers(schema_name)
    url = f"{base_url}/rest/v1/"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, headers=headers)
        _log_supabase_debug(
            method="GET",
            url=url,
            headers=headers,
            params=None,
            response=response,
        )
        _raise_for_supabase_response(
            response,
            schema_name=schema_name,
            table_name="(openapi)",
        )
        spec = response.json()

    tables = []
    for path in spec.get("paths", {}):
        name = path.strip("/")
        if name and "{" not in name and not name.startswith("rpc/"):
            tables.append(name)
    return sorted(set(tables))


async def fetch_table_rows(
    table: str | None = None,
    schema: str | None = None,
) -> list[dict[str, Any]]:
    """Lee filas via Supabase REST. Devuelve siempre un array JSON."""
    base_url = (settings.SUPABASE_URL or "").rstrip("/")
    table_name = (table or settings.SUPABASE_SYNC_TABLE or "").strip()
    schema_name = _normalize_schema(schema)

    if not base_url or not _service_key():
        raise SupabaseSyncError(
            "Configura SUPABASE_URL y SUPABASE_SERVICE_KEY en .env"
        )
    if not table_name:
        raise SupabaseSyncError(
            "Indica tabla en SUPABASE_SYNC_TABLE o en el body del sync"
        )

    url = f"{base_url}/rest/v1/{table_name}"
    headers = _rest_headers(schema_name)
    params = {"select": "*"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            _log_supabase_debug(
                method="GET",
                url=url,
                headers=headers,
                params=params,
                response=response,
            )
            if response.status_code == 404:
                available = await list_supabase_tables(schema_name)
                raise SupabaseSyncError(
                    f"Tabla '{schema_name}.{table_name}' no encontrada. "
                    f"Disponibles en schema '{schema_name}': "
                    f"{', '.join(available) or '(ninguna)'}. "
                    "Expone el schema en Supabase: Settings -> API -> Exposed schemas."
                )
            _raise_for_supabase_response(
                response,
                schema_name=schema_name,
                table_name=table_name,
            )
            rows = response.json()
    except httpx.HTTPError as exc:
        logger.error(f"Supabase REST error: {exc}")
        raise SupabaseSyncError(f"No se pudo leer Supabase: {exc}") from exc

    if not isinstance(rows, list):
        raise SupabaseSyncError(
            "Respuesta inesperada de Supabase REST (se esperaba un array JSON). "
            f"Tipo recibido: {type(rows).__name__}. "
            "Verifica que no se use Accept: application/vnd.pgrst.object+json."
        )

    return rows


async def sync_table_to_qdrant(
    table: str | None = None,
    schema: str | None = None,
) -> dict[str, Any]:
    """Indexa en Qdrant todas las filas de documentos_tecnicos."""
    table_name = (table or settings.SUPABASE_SYNC_TABLE or "").strip()
    schema_name = _normalize_schema(schema)
    rows = await fetch_table_rows(table_name, schema_name)
    service = IncrementalIngestService()

    indexed = 0
    skipped = 0
    errors: list[str] = []

    for row in rows:
        try:
            result = await service.ingest_record(table=table_name, record=row)
            if result.get("skipped"):
                skipped += 1
            else:
                indexed += 1
        except IncrementalIngestError as exc:
            errors.append(str(exc))

    return {
        "schema": schema_name,
        "table": table_name,
        "total_rows": len(rows),
        "indexed": indexed,
        "skipped": skipped,
        "errors": errors,
    }
