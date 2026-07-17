"""Reranker semántico basado en CrossEncoder (sentence-transformers)."""

from __future__ import annotations

import asyncio
from typing import Any

import torch
from sentence_transformers import CrossEncoder

from app.core.config import settings
from app.core.logger import logger


def _resolve_device(configured: str | None = None) -> str:
    """Selecciona el device de inferencia: config → cuda → mps → cpu."""
    if configured:
        return configured

    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class Reranker:
    """
    Reordena chunks recuperados con un CrossEncoder de Hugging Face.

    El modelo se carga en ``__init__`` y debe instanciarse una sola vez
    (vía ``get_reranker()``) para reutilizar pesos entre requests.
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
    ) -> None:
        self.model_name = (model_name or settings.RERANKER_MODEL_NAME).strip()
        self.device = _resolve_device(device or (settings.RERANKER_DEVICE or None))
        logger.info(
            f"Cargando CrossEncoder reranker: {self.model_name} | device={self.device}"
        )
        self.model = CrossEncoder(self.model_name, device=self.device)
        logger.info(f"Reranker inicializado con modelo: {self.model_name}")

    def _predict_scores(self, query: str, chunks: list[dict[str, Any]]) -> list[float]:
        """Calcula scores de relevancia query–documento en batch (CPU/GPU)."""
        pairs = [[query, (chunk.get("text") or "")] for chunk in chunks]
        with torch.inference_mode():
            scores = self.model.predict(
                pairs,
                batch_size=settings.RERANKER_BATCH_SIZE,
                show_progress_bar=False,
            )
        if hasattr(scores, "tolist"):
            return [float(score) for score in scores.tolist()]
        return [float(score) for score in scores]

    async def rerank(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Reordena ``chunks`` por relevancia respecto a ``query``.

        Args:
            query: Consulta de recuperación.
            chunks: Fragmentos de Qdrant (deben incluir ``text``).
            top_k: Si se indica, limita el resultado a los N mejores tras el score.
                Si es ``None``, usa ``settings.TOP_K``. El pipeline puede
                recortar de nuevo con ``max_chunks``.

        Returns:
            Lista de chunks ordenada de mayor a menor ``rerank_score``.
            Ante error, conserva el orden vectorial original.
        """
        if not chunks or len(chunks) <= 1:
            return chunks

        effective_top_k = top_k if top_k is not None else settings.TOP_K
        logger.info(
            f"Rerank con {self.model_name} iniciado para {len(chunks)} chunks "
            f"(top_k={effective_top_k}, device={self.device})"
        )

        try:
            scores = await asyncio.to_thread(self._predict_scores, query, chunks)

            scored: list[tuple[float, dict[str, Any]]] = []
            for chunk, score in zip(chunks, scores, strict=True):
                chunk["rerank_score"] = score
                scored.append((score, chunk))

            scored.sort(key=lambda item: item[0], reverse=True)
            reranked = [chunk for _, chunk in scored]

            if effective_top_k is not None and effective_top_k > 0:
                reranked = reranked[:effective_top_k]

            logger.info(
                f"Reranking completado | modelo={self.model_name} | "
                f"chunks={len(reranked)} | top_k={effective_top_k}"
            )
            return reranked

        except Exception as error:
            logger.warning(
                f"Error en CrossEncoder rerank, usando orden vectorial por defecto: {error}"
            )
            for chunk in chunks:
                chunk["rerank_score"] = float(chunk.get("score") or 0.0)
            return chunks
