from app.core.prompts import CONVERSATION_SUMMARY_PROMPT
from app.core.logger import logger
from app.llm.base import BaseLLMProvider
from app.rag.schemas import ChatMessage, RAGRequest

SUMMARY_REFRESH_INTERVAL = 3


def should_refresh_summary(request: RAGRequest) -> bool:
    """Regenera el summary cada N mensajes del usuario (default: 3)."""
    return request.current_user_message_index() % SUMMARY_REFRESH_INTERVAL == 0


class ConversationSummarizer:
    """Actualiza el resumen conversacional mediante una llamada dedicada al LLM."""

    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    async def summarize(
        self,
        previous_summary: str,
        recent_messages: list[ChatMessage],
        user_message: str,
        assistant_answer: str,
    ) -> str:
        recent_text = self._format_messages(recent_messages)
        prompt = CONVERSATION_SUMMARY_PROMPT.format(
            previous_summary=previous_summary.strip() or "(sin resumen previo)",
            recent_messages=recent_text or "(ninguno)",
            user_message=user_message,
            assistant_answer=assistant_answer,
        )

        logger.info("Generando summary conversacional")
        summary = await self.llm.generate_response_async(
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3, "num_predict": 256},
        )
        return summary.strip()

    @staticmethod
    def _format_messages(messages: list[ChatMessage]) -> str:
        return "\n".join(f"{message.role}: {message.content}" for message in messages)
