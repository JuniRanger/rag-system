from app.core.config import settings
from app.core.logger import logger

class TextChunker:
    def __init__(self):
        self.chunk_size = settings.CHUNK_SIZE
        self.chunk_overlap = settings.CHUNK_OVERLAP

    def chunk(self, text: str, metadata: dict = {}) -> list[dict]:
        """Divide el texto en fragmentos con solapamiento."""
        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self.chunk_size

            # Si no es el último fragmento, busca un corte limpio
            if end < len(text):
                end = self._find_clean_break(text, end)

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "chunk_index": chunk_index,
                    "start_char": start,
                    "end_char": end,
                    "char_count": len(chunk_text),
                    **metadata  # filename, file_path, file_type vienen del loader
                })
                chunk_index += 1

            # El siguiente fragmento empieza con solapamiento
            start = end - self.chunk_overlap

        logger.info(f"Documento dividido en {len(chunks)} fragmentos")
        return chunks

    def _find_clean_break(self, text: str, position: int) -> int:
        """
        Busca el mejor punto de corte cerca de la posición dada.
        Prioridad: párrafo > oración > palabra
        """
        # Busca salto de párrafo en ventana de 200 caracteres
        window = text[max(0, position-200):position+200]
        
        paragraph_break = window.rfind('\n\n')
        if paragraph_break != -1:
            return max(0, position-200) + paragraph_break + 2

        # Si no hay párrafo, busca fin de oración
        for punct in ['. ', '! ', '? ']:
            sentence_break = window.rfind(punct)
            if sentence_break != -1:
                return max(0, position-200) + sentence_break + 2

        # Si no hay oración, corta en espacio (nunca parte palabras)
        space_break = text.rfind(' ', position-50, position)
        if space_break != -1:
            return space_break + 1

        return position