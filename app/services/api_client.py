"""Cliente HTTP compartido para tools que consumen APIs internas protegidas.

Todas las solicitudes incluyen ``X-Internal-Secret``. Las tools no deben
conocer ni loguear el secreto; solo usan ``get`` / ``post`` / etc.
"""

from __future__ import annotations

from typing import Any, Mapping

import httpx

from app.core.config import settings
from app.core.logger import logger

DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_CONNECT_TIMEOUT_SECONDS = 10.0
INTERNAL_SECRET_HEADER = "X-Internal-Secret"


class InternalApiError(Exception):
    """Error seguro para tools/LLM: nunca incluye el secreto ni headers."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_type: str = "http_error",
    ) -> None:
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(message)


class InternalApiClient:
    """
    Wrapper de ``httpx.AsyncClient`` con autenticación interna automática.

    Extensible: timeouts, headers comunes, logging y política de errores
    viven aquí. Las tools solo llaman ``await api_client.post(...)``.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        secret: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        connect_timeout: float = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        resolved_secret = (secret if secret is not None else settings.INTERNAL_API_SECRET) or ""
        resolved_secret = resolved_secret.strip()
        if not resolved_secret:
            raise RuntimeError(
                "INTERNAL_API_SECRET no está configurada. "
                "Define la variable de entorno antes de usar el cliente HTTP interno."
            )

        self._secret = resolved_secret
        self._base_url = (base_url if base_url is not None else "").rstrip("/")
        self._timeout = httpx.Timeout(timeout, connect=connect_timeout)
        self._extra_headers = dict(default_headers or {})
        self._client: httpx.AsyncClient | None = None

    @property
    def base_url(self) -> str:
        return self._base_url

    def _auth_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            **self._extra_headers,
            INTERNAL_SECRET_HEADER: self._secret,
        }
        return headers

    def _merge_headers(self, headers: Mapping[str, str] | None) -> dict[str, str]:
        merged = self._auth_headers()
        if headers:
            merged.update(headers)
            # El secreto interno siempre gana; las tools no pueden sobrescribirlo.
            merged[INTERNAL_SECRET_HEADER] = self._secret
        return merged

    def _resolve_url(self, url: str) -> str:
        if url.startswith(("http://", "https://")):
            return url
        if not self._base_url:
            return url
        return f"{self._base_url}/{url.lstrip('/')}"

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url or None,
                timeout=self._timeout,
                headers=self._auth_headers(),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        client = await self._ensure_client()
        resolved = self._resolve_url(url)
        safe_method = method.upper()
        logger.info(f"Internal API {safe_method} {resolved}")

        # Con base_url configurada, preferir path relativo; si ya es absoluta, usarla tal cual.
        request_url = url if url.startswith(("http://", "https://")) else (
            url if self._base_url else resolved
        )

        try:
            response = await client.request(
                safe_method,
                request_url,
                headers=self._merge_headers(headers),
                **kwargs,
            )
        except httpx.TimeoutException as error:
            logger.error(f"Internal API timeout | {safe_method} {resolved} | type={type(error).__name__}")
            raise InternalApiError(
                "La API interna no respondió a tiempo. Intenta de nuevo.",
                error_type="timeout",
            ) from None
        except httpx.ConnectError:
            logger.error(f"Internal API connection error | {safe_method} {resolved}")
            raise InternalApiError(
                "No se pudo conectar con la API interna.",
                error_type="connection",
            ) from None
        except httpx.HTTPError as error:
            logger.error(
                f"Internal API transport error | {safe_method} {resolved} | "
                f"type={type(error).__name__}"
            )
            raise InternalApiError(
                "Error de red al contactar la API interna.",
                error_type="transport",
            ) from None

        return self._handle_response(response, method=safe_method, url=resolved)

    def _handle_response(
        self,
        response: httpx.Response,
        *,
        method: str,
        url: str,
    ) -> httpx.Response:
        status = response.status_code
        logger.info(f"Internal API {method} {url} → HTTP {status}")

        if status == 401:
            raise InternalApiError(
                "La API interna rechazó la autenticación.",
                status_code=401,
                error_type="unauthorized",
            )
        if status == 403:
            raise InternalApiError(
                "La API interna denegó el acceso.",
                status_code=403,
                error_type="forbidden",
            )
        if status >= 500:
            raise InternalApiError(
                "La API interna tuvo un error interno. Intenta más tarde.",
                status_code=status,
                error_type="server_error",
            )
        return response

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)

    async def patch(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self.request("DELETE", url, **kwargs)


_api_client: InternalApiClient | None = None


def get_api_client(*, base_url: str | None = None) -> InternalApiClient:
    """
    Singleton del cliente interno.

    ``base_url`` solo aplica en la primera inicialización (p. ej. CITAS_API_BASE_URL).
    """
    global _api_client
    if _api_client is None:
        resolved_base = (
            base_url
            if base_url is not None
            else (settings.CITAS_API_BASE_URL or "").rstrip("/")
        )
        _api_client = InternalApiClient(base_url=resolved_base or None)
        logger.info(
            "Cliente HTTP interno inicializado "
            f"(base_url={'set' if resolved_base else 'none'}, auth=X-Internal-Secret)"
        )
    return _api_client


def require_internal_api_secret() -> None:
    """Valida en startup que el secreto exista (sin revelar su valor)."""
    if not (settings.INTERNAL_API_SECRET or "").strip():
        raise RuntimeError(
            "INTERNAL_API_SECRET no está configurada. "
            "Es requerida para tools que llaman APIs HTTP internas."
        )


async def close_api_client() -> None:
    global _api_client
    if _api_client is not None:
        await _api_client.aclose()
        _api_client = None
