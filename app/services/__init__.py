"""Servicios compartidos del backend (clientes HTTP, etc.)."""

from app.services.api_client import (
    InternalApiClient,
    InternalApiError,
    close_api_client,
    get_api_client,
    require_internal_api_secret,
)

__all__ = [
    "InternalApiClient",
    "InternalApiError",
    "close_api_client",
    "get_api_client",
    "require_internal_api_secret",
]
