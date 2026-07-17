from unittest.mock import patch

from app.core.config import Settings


def _settings(**kwargs) -> Settings:
    defaults = {
        "qdrant_url": "https://example.qdrant.io:6333",
        "qdrant_api_key": "test-key",
        "OLLAMA_BASE_URL": "",
        "OLLAMA_BASE_URL_LOCAL": "http://localhost:11434",
        "OLLAMA_BASE_URL_DOCKER": "http://172.17.0.1:11434",
    }
    defaults.update(kwargs)
    return Settings(**defaults)


def test_ollama_url_uses_local_outside_docker():
    with patch("app.core.config.is_running_in_docker", return_value=False):
        settings = _settings()
        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.ollama_runtime == "local"


def test_ollama_url_uses_docker_inside_container():
    with patch("app.core.config.is_running_in_docker", return_value=True):
        settings = _settings()
        assert settings.ollama_base_url == "http://172.17.0.1:11434"
        assert settings.ollama_runtime == "docker"


def test_ollama_url_override_wins():
    with patch("app.core.config.is_running_in_docker", return_value=True):
        settings = _settings(OLLAMA_BASE_URL="http://10.0.0.5:11434")
        assert settings.ollama_base_url == "http://10.0.0.5:11434"
        assert settings.ollama_runtime == "override"
