import json
import ollama
from app.core.config import settings
from app.core.prompts import RERANK_PROMPT
from app.core.logger import logger

class Reranker:
    def __init__(self):
        # Leemos el modelo configurado en tu archivo .env (qwen2.5:3b)
        self.model = settings.OLLAMA_MODEL
        logger.info(f"Reranker inicializado dinámicamente con el modelo: {self.model}")

    def rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        """
        Usa el LLM configurado en el .env para evaluar y ordenar TODOS los chunks
        en una sola llamada (Batching) para optimizar drásticamente la latencia.
        """
        # Si no hay chunks o es solo uno, no tiene sentido gastar tiempo reordenando
        if not chunks or len(chunks) <= 1:
            return chunks

        logger.info(f" Rerank con {self.model} en Batch iniciado para {len(chunks)} chunks")

        # 1. Empaquetar dinámicamente todos los chunks en un solo bloque con IDs numéricos
        chunks_input = ""
        for idx, chunk in enumerate(chunks):
            # Usamos chunk.get o chunk[] según tu estructura de diccionario
            text_snippet = chunk.get("text", "")[:settings.CHUNK_SIZE]
            chunks_input += f"[ID: {idx}]\n{text_snippet}\n\n"

        # 2. Formatear el prompt pasándole la pregunta y los chunks empaquetados
        # Asegúrate de que tu RERANK_PROMPT en prompts.py acepte las variables {question} y {chunks}
        prompt = RERANK_PROMPT.format(question=query, chunks=chunks_input)

        try:
            # 3. Una única llamada a Ollama para evaluar todo el grupo de golpe
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={
                    "temperature": 0.0,
                    "num_predict": 60
                },
                keep_alive=settings.OLLAMA_KEEP_ALIVE,
            )
            
            output_text = response["message"]["content"].strip()
            
            # Limpiar la respuesta por si Qwen llega a meter la respuesta dentro de bloques markdown ```json ... ```
            if "```" in output_text:
                output_text = output_text.split("```json")[-1].split("```")[0].strip()
                
            # Parseamos el array de IDs en orden de relevancia (ej. [2, 0, 1, 3])
            ordered_ids = json.loads(output_text)
            
            # 4. Reordenar tu lista original de chunks mapeando contra los IDs devueltos
            reranked_chunks = []
            for position, _id in enumerate(ordered_ids):
                try:
                    idx_int = int(_id)
                    if 0 <= idx_int < len(chunks):
                        # Asignamos un score artificial descendente (10.0 a 1.0) para mantener consistencia en tus logs
                        chunks[idx_int]["rerank_score"] = max(10.0 - (position * 1.5), 1.0)
                        reranked_chunks.append(chunks[idx_int])
                except (ValueError, TypeError):
                    continue
            
            # Respaldar por seguridad: Si el LLM olvidó o ignoró algún ID en su JSON, 
            # lo metemos al final de la lista para no perder datos en la respuesta.
            for original_chunk in chunks:
                if original_chunk not in reranked_chunks:
                    original_chunk["rerank_score"] = 0.0
                    reranked_chunks.append(original_chunk)

            logger.info("Batch Reranking completado con éxito con el LLM local")
            return reranked_chunks

        except Exception as e:
            logger.warning(f"Error en batch rerank, usando orden vectorial por defecto: {e}")
            # Si el parseo o la llamada fallan, devolvemos la lista original sin romper la petición
            for c in chunks:
                c["rerank_score"] = c.get("score", 5.0)
            return chunks