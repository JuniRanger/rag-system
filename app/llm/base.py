from abc import ABC, abstractmethod


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

    def is_available(self) -> bool:
        """Verifica si el proveedor está disponible."""
        return True
