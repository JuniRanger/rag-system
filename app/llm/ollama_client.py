from functools import lru_cache

import ollama

from app.core.config import settings


@lru_cache
def get_ollama_client() -> ollama.Client:
    """Cliente Ollama singleton configurado desde OLLAMA_BASE_URL."""
    return ollama.Client(host=settings.OLLAMA_BASE_URL)


def get_ollama_base_url() -> str:
    return settings.OLLAMA_BASE_URL.rstrip("/")
