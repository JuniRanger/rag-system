from functools import lru_cache

from app.core.config import settings
from app.core.llm_models import DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_MODEL_FALLBACK
from app.core.logger import logger
from app.llm.ollama_client import get_ollama_client


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


def _model_candidates() -> list[str]:
    requested = (settings.OLLAMA_MODEL or DEFAULT_OLLAMA_MODEL).strip()
    fallback = (settings.OLLAMA_MODEL_FALLBACK or DEFAULT_OLLAMA_MODEL_FALLBACK).strip()

    candidates: list[str] = []
    for model in (requested, fallback, DEFAULT_OLLAMA_MODEL):
        if model and model not in candidates:
            candidates.append(model)
    return candidates


def resolve_ollama_model(client=None, *, force_refresh: bool = False) -> str:
    """
    Resuelve el modelo Ollama a usar: configurado → fallback → default.
    Devuelve el nombre exacto instalado en Ollama.
    """
    if force_refresh:
        get_active_ollama_model.cache_clear()

    ollama_client = client or get_ollama_client()
    available = _list_installed_models(ollama_client)
    requested = (settings.OLLAMA_MODEL or DEFAULT_OLLAMA_MODEL).strip()

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
            return installed

    available_text = ", ".join(available) if available else "(ninguno)"
    raise RuntimeError(
        f"Ningún modelo Ollama disponible. "
        f"Probados: {_model_candidates()}. Instalados: {available_text}. "
        f"Ejecuta: ollama pull {DEFAULT_OLLAMA_MODEL}"
    )


@lru_cache
def get_active_ollama_model() -> str:
    """Modelo Ollama activo tras validación y fallback (singleton)."""
    return resolve_ollama_model()
