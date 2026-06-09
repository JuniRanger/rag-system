#!/usr/bin/env python3
"""Prueba directa Supabase REST — equivalente al snippet del usuario."""
import os
import sys

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.ingestion.supabase_sync import _rest_headers, fetch_table_rows


def test_minimal_request() -> None:
    url = f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/documentos_tecnicos"
    key = settings.SUPABASE_SERVICE_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    response = httpx.get(url, headers=headers, params={"select": "*", "limit": "1"}, timeout=30)
    print("=== minimal (requests-style) ===")
    print("URL:", response.request.url)
    print("status:", response.status_code)
    print("body:", response.text[:500])


async def test_app_client() -> None:
    print("\n=== app fetch_table_rows() ===")
    rows = await fetch_table_rows("documentos_tecnicos", settings.SUPABASE_SCHEMA)
    print("rows:", len(rows))
    if rows:
        print("first keys:", list(rows[0].keys())[:8])


def test_app_headers() -> None:
    print("\n=== app _rest_headers() ===")
    print(_rest_headers(settings.SUPABASE_SCHEMA))


if __name__ == "__main__":
    test_minimal_request()
    test_app_headers()
    import asyncio

    asyncio.run(test_app_client())
