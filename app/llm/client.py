from app.llm.providers.ollama import OllamaLLMProvider
from app.llm.ollama_client import get_ollama_base_url, get_ollama_client

OllamaClient = OllamaLLMProvider

__all__ = ["OllamaClient", "OllamaLLMProvider", "get_ollama_base_url", "get_ollama_client"]