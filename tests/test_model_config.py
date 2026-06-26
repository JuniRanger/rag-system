from unittest.mock import MagicMock, patch

import pytest

from app.core.llm_models import DEFAULT_OLLAMA_MODEL, DEFAULT_OLLAMA_MODEL_FALLBACK
from app.llm.model_config import (
    _find_installed_model,
    _model_candidates,
    get_active_ollama_model,
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
    available = ["llama3.2:1b", "llama3.2:3b"]
    assert _find_installed_model("llama3.2:1b", available) == "llama3.2:1b"


def test_resolve_ollama_model_uses_configured_when_available():
    client = MagicMock()
    client.list.return_value = {"models": [{"name": "llama3.2:3b"}]}

    with patch("app.llm.model_config.settings") as mock_settings:
        mock_settings.OLLAMA_MODEL = "llama3.2:3b"
        mock_settings.OLLAMA_MODEL_FALLBACK = DEFAULT_OLLAMA_MODEL_FALLBACK
        get_active_ollama_model.cache_clear()

        assert resolve_ollama_model(client) == "llama3.2:3b"


def test_resolve_ollama_model_falls_back_to_primary():
    client = MagicMock()
    client.list.return_value = {"models": [{"name": "llama3.2:1b"}]}

    with patch("app.llm.model_config.settings") as mock_settings:
        mock_settings.OLLAMA_MODEL = "qwen2.5:3b"
        mock_settings.OLLAMA_MODEL_FALLBACK = DEFAULT_OLLAMA_MODEL_FALLBACK
        get_active_ollama_model.cache_clear()

        assert resolve_ollama_model(client) == "llama3.2:1b"


def test_resolve_ollama_model_raises_when_none_available():
    client = MagicMock()
    client.list.return_value = {"models": []}

    with patch("app.llm.model_config.settings") as mock_settings:
        mock_settings.OLLAMA_MODEL = "missing:1b"
        mock_settings.OLLAMA_MODEL_FALLBACK = "also-missing:3b"
        get_active_ollama_model.cache_clear()

        with pytest.raises(RuntimeError, match="Ningún modelo Ollama disponible"):
            resolve_ollama_model(client)
