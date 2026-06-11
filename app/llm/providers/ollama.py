import ollama

from app.core.config import settings
from app.core.logger import logger
from app.llm.base import BaseLLMProvider


class OllamaLLMProvider(BaseLLMProvider):
    def __init__(self):
        self.model = settings.OLLAMA_MODEL
        self.base_url = settings.OLLAMA_BASE_URL
        self._verify_connection()

    def _verify_connection(self):
        """Verifica que Ollama está corriendo y el modelo está disponible."""
        try:
            models = ollama.list()
            available = [m["name"] for m in models["models"]]

            if self.model not in available:
                logger.warning(f"Modelo '{self.model}' no encontrado. Disponibles: {available}")
                logger.warning(f"Ejecuta: ollama pull {self.model}")
            else:
                logger.info(f"Modelo '{self.model}' verificado — calentando...")
                ollama.chat(
                    model=self.model,
                    messages=[{"role": "user", "content": "ok"}],
                    options={"num_predict": 1},
                    keep_alive=settings.OLLAMA_KEEP_ALIVE,
                )
                logger.info(f" Modelo '{self.model}' caliente en memoria VRAM")
        except Exception as e:
            logger.error(f"No se puede conectar a Ollama: {e}")
            logger.error("Asegúrate de que Ollama está corriendo con: ollama serve")

    def generate_response(
        self,
        messages: list[dict],
        stream: bool = False,
        options: dict = None,
    ) -> str:
        """
        Envía mensajes al LLM y retorna la respuesta.
        messages: lista de dicts con 'role' y 'content'
        """
        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                stream=stream,
                options=options,
                keep_alive=settings.OLLAMA_KEEP_ALIVE,
            )

            if stream:
                return response  # Retorna el generador para streaming

            content = response["message"]["content"]
            logger.debug(f"LLM respondió: {len(content)} caracteres")
            return content

        except Exception as e:
            logger.error(f"Error en llamada al LLM: {e}")
            raise

    def chat(self, messages: list[dict], stream: bool = False) -> str:
        return self.generate_response(messages, stream=stream)

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        options: dict = None,
    ) -> dict:
        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                tools=tools,
                stream=False,
                options=options,
                keep_alive=settings.OLLAMA_KEEP_ALIVE,
            )
            return response["message"]
        except Exception as e:
            logger.error(f"Error en tool calling con Ollama: {e}")
            raise

    def is_available(self) -> bool:
        """Verifica si Ollama está disponible en este momento."""
        try:
            ollama.list()
            return True
        except Exception:
            return False


OllamaClient = OllamaLLMProvider
