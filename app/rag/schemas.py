from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str = Field(..., min_length=1)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        return value.strip()


class RAGQueryOptions(BaseModel):
    use_reranker: bool = True
    top_k: int = Field(default=5, ge=1, le=50)
    max_chunks: int = Field(default=3, ge=1, le=20)


class RAGRequest(BaseModel):
    conversation_id: Optional[str] = None
    summary: str = ""
    recent_messages: list[ChatMessage] = Field(default_factory=list)
    message: ChatMessage
    options: RAGQueryOptions = Field(default_factory=RAGQueryOptions)

    model_config = {
        "json_schema_extra": {
            "example": {
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "summary": "Usuario consulta problemas mecánicos Hyundai.",
                "recent_messages": [
                    {"role": "user", "content": "Tengo problemas de transmisión"},
                    {"role": "assistant", "content": "¿Qué vehículo tienes?"},
                ],
                "message": {
                    "role": "user",
                    "content": "¿Hay reportes para un Hyundai Santa Fe 2016?",
                },
                "options": {
                    "use_reranker": True,
                    "top_k": 5,
                    "max_chunks": 3,
                },
            }
        }
    }

    def resolved_conversation_id(self) -> str:
        return self.conversation_id or str(uuid4())

    def effective_query(self) -> str:
        return self.message.content.strip()


class SourceReference(BaseModel):
    document_id: str
    score: float
    label: Optional[str] = None


class FunctionCallRecord(BaseModel):
    name: str
    arguments: dict = Field(default_factory=dict)
    status: str
    output: Optional[str] = None


class RAGResponseMetadata(BaseModel):
    latency_ms: int = 0
    retrieved_chunks: int = 0
    used_chunks: int = 0
    tokens_input: int = 0
    tokens_output: int = 0
    tools_used: list[FunctionCallRecord] = Field(default_factory=list)
    function_calls: list[FunctionCallRecord] = Field(default_factory=list)
    context_used: list[dict] = Field(default_factory=list)


class RAGResponse(BaseModel):
    success: bool
    conversation_id: str
    answer: str
    sources: list[SourceReference] = Field(default_factory=list)
    metadata: RAGResponseMetadata = Field(default_factory=RAGResponseMetadata)
