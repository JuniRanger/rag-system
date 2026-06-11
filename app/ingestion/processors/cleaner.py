import re
from app.core.logger import logger

class TextCleaner:
    def clean(self, text: str) -> str:
        """Pipeline completo de limpieza de texto."""
        logger.debug(f"Limpiando texto: {len(text)} caracteres originales")

        text = self._remove_extra_whitespace(text)
        text = self._remove_special_characters(text)
        text = self._normalize_punctuation(text)
        text = self._remove_empty_lines(text)

        logger.debug(f"Texto limpio: {len(text)} caracteres")
        return text.strip()

    def _remove_extra_whitespace(self, text: str) -> str:
        # Reemplaza múltiples espacios/tabs por uno solo
        return re.sub(r'[ \t]+', ' ', text)

    def _remove_special_characters(self, text: str) -> str:
        # Conserva letras, números, puntuación básica y acentos en español
        return re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)\[\]\{\}\"\'áéíóúÁÉÍÓÚñÑüÜ]', ' ', text)

    def _normalize_punctuation(self, text: str) -> str:
        # Elimina espacios antes de signos de puntuación
        return re.sub(r'\s+([\.,:;!?])', r'\1', text)

    def _remove_empty_lines(self, text: str) -> str:
        # Colapsa múltiples líneas vacías en una sola
        return re.sub(r'\n{3,}', '\n\n', text)