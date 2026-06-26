import asyncio

from app.core.config import settings
from app.core.logger import logger
from app.llm.base import BaseLLMProvider
from app.llm.model_config import get_active_ollama_model, resolve_ollama_model
from app.llm.ollama_client import get_ollama_client

_STREAM_END = object()


def _stream_next_chunk(stream) -> object:
    try:
        chunk = next(stream)
    except StopIteration:
        return _STREAM_END
    return chunk.get("message", {}).get("content", "") or ""


def _is_model_not_found_error(error: Exception) -> bool:
    message = str(error).lower()
    return "not found" in message or "does not exist" in message


class OllamaLLMProvider(BaseLLMProvider):
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self._client = get_ollama_client()
        self.model = get_active_ollama_model()
        self._verify_connection()

    def _resolve_model_on_failure(self) -> bool:
        """Reintenta resolver el modelo si el configurado dejó de existir."""
        previous = self.model
        self.model = resolve_ollama_model(self._client, force_refresh=True)
        return self.model != previous

    def _verify_connection(self, *, _retried: bool = False):
        """Verifica Ollama, resuelve el modelo y lo calienta en memoria."""
        try:
            logger.info(f"Modelo LLM activo: {self.model}")
            self._client.chat(
                model=self.model,
                messages=[{"role": "user", "content": "ok"}],
                options={"num_predict": 1},
                keep_alive=settings.OLLAMA_KEEP_ALIVE,
            )
            logger.info(f"Modelo '{self.model}' caliente en memoria VRAM")
        except Exception as e:
            if (
                not _retried
                and _is_model_not_found_error(e)
                and self._resolve_model_on_failure()
            ):
                logger.warning(f"Modelo anterior no disponible; reintentando con '{self.model}'")
                return self._verify_connection(_retried=True)

            logger.error(f"No se puede conectar a Ollama ({self.base_url}): {e}")
            logger.error("Asegúrate de que Ollama está corriendo y OLLAMA_BASE_URL es correcto")

    def _chat(self, **kwargs):
        return self._client.chat(
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
            **kwargs,
        )

    def generate_response(
        self,
        messages: list[dict],
        stream: bool = False,
        options: dict = None,
        _retried: bool = False,
    ) -> str:
        """
        Envía mensajes al LLM y retorna la respuesta.
        messages: lista de dicts con 'role' y 'content'
        """
        try:
            response = self._chat(
                model=self.model,
                messages=messages,
                stream=stream,
                options=options,
            )

            if stream:
                return response

            content = response["message"]["content"]
            logger.debug(f"LLM respondió: {len(content)} caracteres")
            return content

        except Exception as e:
            if (
                not _retried
                and _is_model_not_found_error(e)
                and self._resolve_model_on_failure()
            ):
                logger.warning(f"Reintentando generación con modelo '{self.model}'")
                return self.generate_response(
                    messages, stream=stream, options=options, _retried=True
                )

            logger.error(f"Error en llamada al LLM: {e}")
            raise

    async def stream_response_async(
        self,
        messages: list[dict],
        options: dict = None,
        _retried: bool = False,
    ):
        try:
            stream = self._chat(
                model=self.model,
                messages=messages,
                stream=True,
                options=options,
            )
        except Exception as e:
            if (
                not _retried
                and _is_model_not_found_error(e)
                and self._resolve_model_on_failure()
            ):
                logger.warning(f"Reintentando streaming con modelo '{self.model}'")
                async for token in self.stream_response_async(
                    messages, options=options, _retried=True
                ):
                    yield token
                return
            raise

        while True:
            chunk = await asyncio.to_thread(_stream_next_chunk, stream)
            if chunk is _STREAM_END:
                break
            if chunk:
                yield chunk

    def chat(self, messages: list[dict], stream: bool = False) -> str:
        return self.generate_response(messages, stream=stream)

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        options: dict = None,
        _retried: bool = False,
    ) -> dict:
        try:
            response = self._chat(
                model=self.model,
                messages=messages,
                tools=tools,
                stream=False,
                options=options,
            )
            return response["message"]
        except Exception as e:
            if (
                not _retried
                and _is_model_not_found_error(e)
                and self._resolve_model_on_failure()
            ):
                logger.warning(f"Reintentando tool calling con modelo '{self.model}'")
                return self.chat_with_tools(
                    messages, tools, options=options, _retried=True
                )

            logger.error(f"Error en tool calling con Ollama: {e}")
            raise

    def is_available(self) -> bool:
        """Verifica si Ollama está disponible en este momento."""
        try:
            self._client.list()
            return True
        except Exception:
            return False


OllamaClient = OllamaLLMProvider
