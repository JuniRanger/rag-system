from functools import lru_cache

import httpx

from app.core.config import settings
from app.core.llm_models import (
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_MODEL_FALLBACK,
    DEFAULT_OLLAMA_RERANKER_MODEL,
)
from app.core.logger import logger
from app.llm.ollama_client import get_ollama_client

_verified: bool = False
_reranker_verified: bool = False


def _is_connection_error(error: Exception) -> bool:
    if isinstance(error, (httpx.ConnectError, httpx.TimeoutException, ConnectionError, OSError)):
        return True
    message = str(error).lower()
    type_name = type(error).__name__.lower()
    return (
        "connect" in type_name
        or "connection refused" in message
        or "connection error" in message
        or "failed to establish" in message
    )


def _list_installed_models(client) -> list[str]:
    response = client.list()
    return [m["name"] for m in response.get("models", [])]


def _matches_model(requested: str, installed: str) -> bool:
    if requested == installed:
        return True

    req_base, _, req_tag = requested.partition(":")
    inst_base, _, inst_tag = installed.partition(":")
    if req_base != inst_base:
        return False
    if not req_tag or not inst_tag:
        return True
    return req_tag == inst_tag


def _find_installed_model(requested: str, available: list[str]) -> str | None:
    for name in available:
        if _matches_model(requested, name):
            return name
    return None


def _configured_model() -> str:
    return (settings.OLLAMA_MODEL or DEFAULT_OLLAMA_MODEL).strip()


def _configured_reranker_model() -> str:
    return (settings.OLLAMA_RERANKER_MODEL or DEFAULT_OLLAMA_RERANKER_MODEL).strip()


def _model_candidates() -> list[str]:
    requested = _configured_model()
    fallback = (settings.OLLAMA_MODEL_FALLBACK or DEFAULT_OLLAMA_MODEL_FALLBACK).strip()

    candidates: list[str] = []
    for model in (requested, fallback, DEFAULT_OLLAMA_MODEL):
        if model and model not in candidates:
            candidates.append(model)
    return candidates


def _reranker_candidates() -> list[str]:
    requested = _configured_reranker_model()
    candidates: list[str] = []
    for model in (requested, DEFAULT_OLLAMA_RERANKER_MODEL):
        if model and model not in candidates:
            candidates.append(model)
    return candidates


def reset_ollama_model_state() -> None:
    global _verified, _reranker_verified
    _verified = False
    _reranker_verified = False
    get_active_ollama_model.cache_clear()
    get_active_ollama_reranker_model.cache_clear()


def is_ollama_model_verified() -> bool:
    return _verified


def is_ollama_reranker_model_verified() -> bool:
    return _reranker_verified


def resolve_ollama_model(client=None, *, force_refresh: bool = False) -> str:
    """
    Resuelve el modelo Ollama a usar: configurado → fallback → default.
    Si Ollama no responde, devuelve el modelo configurado sin verificar.
    """
    global _verified

    if force_refresh:
        reset_ollama_model_state()

    ollama_client = client or get_ollama_client()
    requested = _configured_model()

    try:
        available = _list_installed_models(ollama_client)
    except Exception as error:
        if _is_connection_error(error):
            logger.warning(
                f"Ollama no alcanzable en {settings.OLLAMA_BASE_URL}: {error}. "
                f"Usando modelo configurado '{requested}' (sin verificar)."
            )
            _verified = False
            return requested
        raise

    for candidate in _model_candidates():
        installed = _find_installed_model(candidate, available)
        if installed:
            if candidate != requested:
                logger.warning(
                    f"Modelo configurado '{requested}' no disponible. "
                    f"Usando '{installed}'."
                )
            elif installed != requested:
                logger.info(f"Modelo resuelto: '{requested}' → '{installed}'")
            _verified = True
            return installed

    available_text = ", ".join(available) if available else "(ninguno)"
    raise RuntimeError(
        f"Ningún modelo Ollama disponible. "
        f"Probados: {_model_candidates()}. Instalados: {available_text}. "
        f"Ejecuta: ollama pull {DEFAULT_OLLAMA_MODEL}"
    )


def resolve_ollama_reranker_model(client=None, *, force_refresh: bool = False) -> str:
    """Resuelve el modelo del reranker (rápido). Fallback a llama3.2:1b."""
    global _reranker_verified

    if force_refresh:
        get_active_ollama_reranker_model.cache_clear()
        _reranker_verified = False

    ollama_client = client or get_ollama_client()
    requested = _configured_reranker_model()

    try:
        available = _list_installed_models(ollama_client)
    except Exception as error:
        if _is_connection_error(error):
            logger.warning(
                f"Ollama no alcanzable para reranker: {error}. "
                f"Usando '{requested}' (sin verificar)."
            )
            _reranker_verified = False
            return requested
        raise

    for candidate in _reranker_candidates():
        installed = _find_installed_model(candidate, available)
        if installed:
            if candidate != requested:
                logger.warning(
                    f"Modelo reranker '{requested}' no disponible. "
                    f"Usando '{installed}'."
                )
            _reranker_verified = True
            return installed

    logger.warning(
        f"Modelo reranker no encontrado; usando configurado '{requested}' sin verificar."
    )
    _reranker_verified = False
    return requested


@lru_cache
def get_active_ollama_model() -> str:
    """Modelo Ollama activo tras validación y fallback (singleton)."""
    return resolve_ollama_model()


@lru_cache
def get_active_ollama_reranker_model() -> str:
    """Modelo Ollama del reranker (singleton)."""
    return resolve_ollama_reranker_model()
