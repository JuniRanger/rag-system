from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.core.llm_models import (
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_MODEL_FALLBACK,
)
from app.llm.model_config import (
    _find_installed_model,
    _model_candidates,
    get_active_ollama_model,
    is_ollama_model_verified,
    reset_ollama_model_state,
    resolve_ollama_model,
)


def test_model_candidates_order():
    with patch("app.llm.model_config.settings") as mock_settings:
        mock_settings.OLLAMA_MODEL = "custom:7b"
        mock_settings.OLLAMA_MODEL_FALLBACK = DEFAULT_OLLAMA_MODEL_FALLBACK

        assert _model_candidates() == [
            "custom:7b",
            DEFAULT_OLLAMA_MODEL_FALLBACK,
            DEFAULT_OLLAMA_MODEL,
        ]


def test_find_installed_model_matches_tag_variants():
    available = ["llama3:8b", "llama3.2:1b"]
    assert _find_installed_model("llama3:8b", available) == "llama3:8b"


def test_resolve_ollama_model_uses_configured_when_available():
    client = MagicMock()
    client.list.return_value = {"models": [{"name": "llama3:8b"}]}

    with patch("app.llm.model_config.settings") as mock_settings:
        mock_settings.OLLAMA_MODEL = "llama3:8b"
        mock_settings.OLLAMA_MODEL_FALLBACK = DEFAULT_OLLAMA_MODEL_FALLBACK
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.ollama_base_url = "http://localhost:11434"
        reset_ollama_model_state()

        assert resolve_ollama_model(client) == "llama3:8b"
        assert is_ollama_model_verified() is True


def test_resolve_ollama_model_falls_back_to_primary():
    client = MagicMock()
    client.list.return_value = {"models": [{"name": "llama3.2:1b"}]}

    with patch("app.llm.model_config.settings") as mock_settings:
        mock_settings.OLLAMA_MODEL = "qwen2.5:3b"
        mock_settings.OLLAMA_MODEL_FALLBACK = DEFAULT_OLLAMA_MODEL_FALLBACK
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.ollama_base_url = "http://localhost:11434"
        reset_ollama_model_state()

        assert resolve_ollama_model(client) == "llama3.2:1b"
        assert is_ollama_model_verified() is True


def test_resolve_ollama_model_returns_unverified_on_connection_error():
    client = MagicMock()
    client.list.side_effect = httpx.ConnectError("Connection refused")

    with patch("app.llm.model_config.settings") as mock_settings:
        mock_settings.OLLAMA_MODEL = "llama3:8b"
        mock_settings.OLLAMA_MODEL_FALLBACK = DEFAULT_OLLAMA_MODEL_FALLBACK
        mock_settings.OLLAMA_BASE_URL = "http://host.docker.internal:11434"
        mock_settings.ollama_base_url = "http://host.docker.internal:11434"
        reset_ollama_model_state()

        assert resolve_ollama_model(client) == "llama3:8b"
        assert is_ollama_model_verified() is False


def test_resolve_ollama_model_raises_when_none_available():
    client = MagicMock()
    client.list.return_value = {"models": []}

    with patch("app.llm.model_config.settings") as mock_settings:
        mock_settings.OLLAMA_MODEL = "missing:1b"
        mock_settings.OLLAMA_MODEL_FALLBACK = "also-missing:3b"
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.ollama_base_url = "http://localhost:11434"
        reset_ollama_model_state()

        with pytest.raises(RuntimeError, match="Ningún modelo Ollama disponible"):
            resolve_ollama_model(client)


def test_get_active_ollama_model_is_cached():
    client = MagicMock()
    client.list.return_value = {"models": [{"name": "llama3:8b"}]}

    with patch("app.llm.model_config.settings") as mock_settings:
        mock_settings.OLLAMA_MODEL = "llama3:8b"
        mock_settings.OLLAMA_MODEL_FALLBACK = DEFAULT_OLLAMA_MODEL_FALLBACK
        mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_settings.ollama_base_url = "http://localhost:11434"
        reset_ollama_model_state()

        with patch("app.llm.model_config.get_ollama_client", return_value=client):
            assert get_active_ollama_model() == "llama3:8b"
            assert get_active_ollama_model() == "llama3:8b"
            client.list.assert_called_once()
