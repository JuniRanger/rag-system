from app.llm.providers.ollama import OllamaLLMProvider
from app.llm.model_config import get_active_ollama_model
from app.llm.ollama_client import get_ollama_base_url, get_ollama_client

OllamaClient = OllamaLLMProvider

__all__ = [
    "OllamaClient",
    "OllamaLLMProvider",
    "get_active_ollama_model",
    "get_ollama_base_url",
    "get_ollama_client",
]