from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.sanitize import DEFAULT_QUERY_MAX_LEN, sanitize_text


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str = Field(..., min_length=1, max_length=DEFAULT_QUERY_MAX_LEN)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        return sanitize_text(value, field="content", max_length=DEFAULT_QUERY_MAX_LEN)


class RAGQueryOptions(BaseModel):
    use_reranker: bool = True
    top_k: int = Field(default=10, ge=1, le=50)
    max_chunks: int = Field(default=10, ge=1, le=20)


class UserPerfil(BaseModel):
    """Perfil del usuario (ragPayload.user.perfil)."""

    model_config = ConfigDict(extra="allow")

    role: Literal["admin", "client"] = "client"


class UsuarioInfo(BaseModel):
    """Datos de cuenta del usuario (ragPayload.user.usuario)."""

    model_config = ConfigDict(extra="allow")

    nombre: Optional[str] = None
    email: Optional[str] = None
    correo: Optional[str] = None
    telefono: Optional[str] = None


class RAGUser(BaseModel):
    """Contexto de usuario enviado por el frontend (ragPayload.user)."""

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    perfil: UserPerfil = Field(default_factory=UserPerfil)
    usuario: Optional[UsuarioInfo] = None

    def cita_usuario_payload(self) -> dict[str, str] | None:
        """DTO de usuario para crearCitaAPI (id, nombre, correo)."""
        user_id = str(self.id or "").strip()
        info = self.usuario
        nombre = str((info.nombre if info else None) or "").strip()
        correo = ""
        if info:
            correo = str(info.correo or info.email or "").strip()
        if not user_id or not nombre or not correo:
            return None
        return {"id": user_id, "nombre": nombre, "correo": correo}

    def to_cita_prompt_text(self) -> str:
        """Bloque legible de cliente en sesión (el servidor adjunta usuario a la tool)."""
        payload = self.cita_usuario_payload()
        if payload:
            return (
                f"id: {payload['id']}\n"
                f"nombre: {payload['nombre']}\n"
                f"correo: {payload['correo']}\n"
                "(el sistema adjunta estos datos automáticamente al agendar)"
            )

        info = self.usuario
        lines = [
            f"id: {self.id or '(faltante)'}",
        ]
        if info:
            lines.append(f"nombre: {info.nombre or '(faltante)'}")
            correo = info.correo or info.email
            lines.append(f"correo: {correo or '(faltante)'}")
        else:
            lines.append("nombre: (faltante)")
            lines.append("correo: (faltante)")
        lines.append(
            "(datos incompletos: no se podrá agendar hasta que el request traiga id, nombre y correo)"
        )
        return "\n".join(lines)


class WorkingMemory(BaseModel):
    """Memoria activa de diagnóstico. Se resetea al cambiar de vehículo."""

    vehicle: str = ""
    problem: str = ""
    topic: str = ""

    def has_active_context(self) -> bool:
        return bool(self.vehicle or self.problem or self.topic)

    def to_prompt_text(self) -> str:
        if not self.has_active_context():
            return "(sin contexto activo de diagnóstico)"
        parts: list[str] = []
        if self.vehicle:
            parts.append(f"Vehículo activo: {self.vehicle}")
        if self.problem:
            parts.append(f"Problema activo: {self.problem}")
        return "\n".join(parts)


class RAGRequest(BaseModel):
    conversation_id: Optional[str] = None
    summary: str = ""
    working_memory: WorkingMemory = Field(default_factory=WorkingMemory)
    recent_messages: list[ChatMessage] = Field(default_factory=list)
    user_message_count: Optional[int] = Field(
        default=None,
        ge=1,
        description="Índice del mensaje actual del usuario en la conversación. "
        "Si no se envía, se infiere desde recent_messages.",
    )
    message: ChatMessage
    options: RAGQueryOptions = Field(default_factory=RAGQueryOptions)
    user: Optional[RAGUser] = Field(
        default=None,
        description="Usuario del frontend: id, perfil.role y usuario.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "summary": "Cliente quiere agendar cambio de balatas.",
                "recent_messages": [
                    {"role": "user", "content": "Quiero agendar una cita"},
                    {"role": "assistant", "content": "Claro, ¿qué vehículo y servicio necesitas?"},
                ],
                "message": {
                    "role": "user",
                    "content": "Mazda 3 2018, balatas delanteras, este jueves a las 10:00",
                },
                "user": {
                    "id": "1",
                    "perfil": {"role": "client"},
                    "usuario": {
                        "nombre": "Cliente Guapo",
                        "correo": "levos@gmail.com",
                        "email": "levos@gmail.com",
                    },
                },
                "options": {"use_reranker": True},
            }
        }
    }

    def resolved_conversation_id(self) -> str:
        return self.conversation_id or str(uuid4())

    def effective_query(self) -> str:
        return self.message.content.strip()

    def user_role(self) -> Literal["admin", "client"]:
        if self.user and self.user.perfil:
            return self.user.perfil.role
        return "client"

    def current_user_message_index(self) -> int:
        if self.user_message_count is not None:
            return self.user_message_count
        prior_user_messages = sum(1 for message in self.recent_messages if message.role == "user")
        return prior_user_messages + 1


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
    ttft_ms: int = 0
    tokens_per_second: float = 0.0
    intent: str = ""
    vehicle_changed: bool = False
    rag_executed: bool = False
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
    summary: str = ""
    working_memory: WorkingMemory = Field(default_factory=WorkingMemory)
    sources: list[SourceReference] = Field(default_factory=list)
    metadata: RAGResponseMetadata = Field(default_factory=RAGResponseMetadata)
