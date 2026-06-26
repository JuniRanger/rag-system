import json
import re

from app.core.config import settings
from app.core.prompts import RERANK_PROMPT
from app.core.logger import logger
from app.llm.base import BaseLLMProvider


class Reranker:
    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm_provider = llm_provider
        self.model = getattr(llm_provider, "model", llm_provider.__class__.__name__)
        logger.info(f"Reranker inicializado dinámicamente con el modelo: {self.model}")

    async def rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        if not chunks or len(chunks) <= 1:
            return chunks

        logger.info(f"Rerank con {self.model} en Batch iniciado para {len(chunks)} chunks (top_k=5)")

        chunks_input = ""
        for idx, chunk in enumerate(chunks):
            text_snippet = chunk.get("text", "")[: settings.CHUNK_SIZE]
            chunks_input += f"[ID: {idx}]\n{text_snippet}\n\n"

        prompt = RERANK_PROMPT.format(question=query, chunks=chunks_input)

        try:
            output_text = (
                await self.llm_provider.generate_response_async(
                    messages=[{"role": "user", "content": prompt}],
                    options={
                        "temperature": 0.0,
                        "num_predict": 100,
                        "format": "json",
                    },
                )
            ).strip()

            fence = "```"
            if fence in output_text:
                match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", output_text)
                if match:
                    output_text = match.group(1).strip()
                else:
                    output_text = output_text.replace("```json", "").replace(fence, "").strip()

            ordered_ids = json.loads(output_text)

            if isinstance(ordered_ids, dict):
                for value in ordered_ids.values():
                    if isinstance(value, list):
                        ordered_ids = value
                        break

            reranked_chunks = []
            if isinstance(ordered_ids, list):
                for position, chunk_id in enumerate(ordered_ids):
                    try:
                        idx_int = int(chunk_id)
                        if 0 <= idx_int < len(chunks):
                            chunks[idx_int]["rerank_score"] = max(10.0 - (position * 1.5), 1.0)
                            reranked_chunks.append(chunks[idx_int])
                    except (ValueError, TypeError):
                        continue

            for original_chunk in chunks:
                if original_chunk not in reranked_chunks:
                    original_chunk["rerank_score"] = 0.0
                    reranked_chunks.append(original_chunk)

            logger.info("Batch Reranking completado con éxito con el LLM local")
            return reranked_chunks

        except Exception as error:
            logger.warning(f"Error en batch rerank, usando orden vectorial por defecto: {error}")
            for chunk in chunks:
                chunk["rerank_score"] = chunk.get("score", 5.0)
            return chunks
