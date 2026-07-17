import asyncio
from unittest.mock import MagicMock, patch

import pytest

from app.retrieval.reranker import Reranker, _resolve_device


def test_resolve_device_respects_configured_value():
    assert _resolve_device("cpu") == "cpu"


def test_rerank_orders_by_cross_encoder_score():
    chunks = [
        {"text": "pieza irrelevante", "score": 0.9},
        {"text": "falla de transmisión", "score": 0.5},
        {"text": "otro texto", "score": 0.7},
    ]

    with patch("app.retrieval.reranker.CrossEncoder") as mock_ce:
        mock_ce.return_value.predict.return_value = [0.1, 0.9, 0.4]
        with patch("app.retrieval.reranker.settings") as mock_settings:
            mock_settings.RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
            mock_settings.RERANKER_DEVICE = "cpu"
            mock_settings.RERANKER_BATCH_SIZE = 16
            mock_settings.TOP_K = 10

            reranker = Reranker(model_name="BAAI/bge-reranker-v2-m3", device="cpu")
            result = asyncio.run(reranker.rerank("problema de transmisión", chunks))

    assert [c["text"] for c in result] == [
        "falla de transmisión",
        "otro texto",
        "pieza irrelevante",
    ]
    assert result[0]["rerank_score"] == pytest.approx(0.9)
    mock_ce.return_value.predict.assert_called_once()


def test_rerank_respects_top_k():
    chunks = [{"text": f"c{i}", "score": 0.1} for i in range(5)]

    with patch("app.retrieval.reranker.CrossEncoder") as mock_ce:
        mock_ce.return_value.predict.return_value = [0.5, 0.1, 0.9, 0.2, 0.8]
        with patch("app.retrieval.reranker.settings") as mock_settings:
            mock_settings.RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
            mock_settings.RERANKER_DEVICE = "cpu"
            mock_settings.RERANKER_BATCH_SIZE = 16
            mock_settings.TOP_K = 10

            reranker = Reranker(device="cpu")
            result = asyncio.run(reranker.rerank("q", chunks, top_k=2))

    assert len(result) == 2
    assert [c["text"] for c in result] == ["c2", "c4"]


def test_rerank_falls_back_on_error():
    chunks = [{"text": "a", "score": 0.6}, {"text": "b", "score": 0.4}]

    with patch("app.retrieval.reranker.CrossEncoder") as mock_ce:
        instance = MagicMock()
        instance.predict.side_effect = RuntimeError("boom")
        mock_ce.return_value = instance
        with patch("app.retrieval.reranker.settings") as mock_settings:
            mock_settings.RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"
            mock_settings.RERANKER_DEVICE = "cpu"
            mock_settings.RERANKER_BATCH_SIZE = 16
            mock_settings.TOP_K = 10

            reranker = Reranker(device="cpu")
            result = asyncio.run(reranker.rerank("q", chunks))

    assert [c["text"] for c in result] == ["a", "b"]
    assert result[0]["rerank_score"] == pytest.approx(0.6)
