from functools import lru_cache

import ollama

from app.core.config import settings


@lru_cache
def get_ollama_client() -> ollama.Client:
    """Cliente Ollama singleton (URL resuelta: local / docker / override)."""
    return ollama.Client(host=settings.ollama_base_url)


def get_OLLAMA_BASE_URL() -> str:
    """URL efectiva de Ollama sin slash final."""
    return settings.ollama_base_url


def get_ollama_base_url() -> str:
    return get_OLLAMA_BASE_URL()
