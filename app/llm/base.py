import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_response(
        self,
        messages: list[dict],
        stream: bool = False,
        options: dict = None,
    ) -> str:
        """Genera una respuesta a partir de una lista de mensajes."""
        raise NotImplementedError

    async def generate_response_async(
        self,
        messages: list[dict],
        stream: bool = False,
        options: dict = None,
    ) -> str:
        """Versión asíncrona; por defecto delega al cliente síncrono en un thread."""
        return await asyncio.to_thread(
            self.generate_response,
            messages,
            stream,
            options,
        )

    async def stream_response_async(
        self,
        messages: list[dict],
        options: dict = None,
    ) -> AsyncIterator[str]:
        """Emite la respuesta completa como un único token si no hay streaming nativo."""
        text = await self.generate_response_async(messages, options=options)
        if text:
            yield text

    def generate(self, prompt: str) -> str:
        """Atajo para llamadas simples con un solo prompt."""
        return self.generate_response([{"role": "user", "content": prompt}])

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        options: dict = None,
    ) -> dict:
        """Genera una respuesta con soporte de herramientas. Por defecto, sin tool calling."""
        content = self.generate_response(messages, options=options)
        return {"role": "assistant", "content": content}

    async def chat_with_tools_async(
        self,
        messages: list[dict],
        tools: list[dict],
        options: dict = None,
    ) -> dict:
        """Versión asíncrona de tool calling."""
        return await asyncio.to_thread(
            self.chat_with_tools,
            messages,
            tools,
            options,
        )

    def is_available(self) -> bool:
        """Verifica si el proveedor está disponible."""
        return True
