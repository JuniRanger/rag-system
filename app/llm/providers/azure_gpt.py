from app.llm.base import BaseLLMProvider


class AzureGPTLLMProvider(BaseLLMProvider):
    def __init__(self):
        raise NotImplementedError("Azure GPT aún no está implementado.")

    def generate_response(
        self,
        messages: list[dict],
        stream: bool = False,
        options: dict = None,
    ) -> str:
        raise NotImplementedError("Azure GPT aún no está implementado.")
