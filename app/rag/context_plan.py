from dataclasses import dataclass

from app.core.logger import logger
from app.rag.intent import (
    REJECT_OUT_OF_SCOPE_REQUEST,
    QueryIntent,
    detect_intent,
    has_explicit_reference,
)
from app.rag.schemas import ChatMessage, RAGRequest, WorkingMemory
from app.rag.vehicle import extract_problem, extract_vehicle, vehicles_are_different

# Filtro estricto de seguridad para mitigar inyecciones o desvíos de contexto
PALABRAS_PROHIBIDAS = [
    "drop database", "drop table", "select * from", "delete from",
    "insert into", "truncate", "sql", "execute command", "escribe un codigo",
    "genera un script", "hack", "system prompt", "instrucciones del sistema",
]


@dataclass(frozen=True)
class GenerationPlan:
    intent: QueryIntent
    run_rag: bool
    use_tools: bool
    tool_mode: str  # "all" | "scheduling" | "none"
    include_conversation_history: bool
    working_memory: WorkingMemory
    vehicle_changed: bool
    retrieval_query: str
    conversation_history: str
    current_question: str
    user_role: str = "client"
    # Texto + payload para que el LLM arme el DTO de crearCitaAPI
    user_profile_text: str = "(sin datos de usuario en el request)"
    cita_usuario: dict[str, str] | None = None


def _format_recent_messages(messages: list[ChatMessage]) -> str:
    if not messages:
        return ""
    return "\n".join(f"{message.role}: {message.content}" for message in messages)


def _update_working_memory(
    previous: WorkingMemory,
    message: str,
    intent: QueryIntent,
    detected_vehicle: str | None,
    vehicle_changed: bool,
) -> WorkingMemory:
    if vehicle_changed:
        memory = WorkingMemory()
    else:
        memory = previous.model_copy()

    if detected_vehicle:
        memory.vehicle = detected_vehicle

    if intent == QueryIntent.AUTOMOTIVE:
        problem = extract_problem(message)
        if problem:
            memory.problem = problem
        if detected_vehicle or problem:
            memory.topic = "automotive_diagnosis"

    if intent == QueryIntent.SCHEDULING:
        memory.topic = "appointment_scheduling"
        problem = extract_problem(message)
        if problem:
            memory.problem = problem

    if intent in {QueryIntent.CONVERSATION, QueryIntent.OUT_OF_SCOPE} and not detected_vehicle:
        if not has_explicit_reference(message):
            memory.topic = ""

    return memory


def _build_retrieval_query(memory: WorkingMemory, message: str) -> str:
    parts: list[str] = []
    if memory.vehicle:
        parts.append(memory.vehicle)
    if memory.problem:
        parts.append(memory.problem)
    parts.append(message)
    return "\n".join(parts)


def plan_request(request: RAGRequest) -> GenerationPlan:
    message = request.effective_query()
    previous_memory = request.working_memory

    contiene_prohibidas = any(palabra in message.lower() for palabra in PALABRAS_PROHIBIDAS)
    intent = detect_intent(message, previous_memory)

    if contiene_prohibidas:
        intent = QueryIntent.OUT_OF_SCOPE

    detected_vehicle = extract_vehicle(message)
    vehicle_changed = vehicles_are_different(detected_vehicle, previous_memory.vehicle)

    working_memory = _update_working_memory(
        previous=previous_memory,
        message=message,
        intent=intent,
        detected_vehicle=detected_vehicle,
        vehicle_changed=vehicle_changed,
    )

    # Diagnóstico → RAG documental. Citas → tools (sin contaminar con documentos técnicos).
    run_rag = intent == QueryIntent.AUTOMOTIVE
    if intent == QueryIntent.SCHEDULING:
        use_tools = True
        tool_mode = "scheduling"
    elif intent == QueryIntent.AUTOMOTIVE:
        use_tools = True
        tool_mode = "all"
    else:
        use_tools = False
        tool_mode = "none"

    if intent == QueryIntent.OUT_OF_SCOPE:
        current_question = REJECT_OUT_OF_SCOPE_REQUEST
        retrieval_query = ""
        include_history = False
    elif intent == QueryIntent.SCHEDULING:
        current_question = message
        # Historial completo ayuda a reunir fecha/vehículo/producto
        include_history = True
        retrieval_query = ""
    else:
        current_question = message
        include_history = intent == QueryIntent.MEMORY_REQUEST or (
            intent == QueryIntent.AUTOMOTIVE and has_explicit_reference(message)
        )
        retrieval_query = _build_retrieval_query(working_memory, message) if run_rag else message

    conversation_history = (
        _format_recent_messages(request.recent_messages) if include_history else ""
    )

    user_profile_text = "(sin datos de usuario en el request)"
    cita_usuario = None
    if request.user:
        user_profile_text = request.user.to_cita_prompt_text()
        cita_usuario = request.user.cita_usuario_payload()

    logger.info(
        f"Plan generado | intent={intent.value} | run_rag={run_rag} | "
        f"use_tools={use_tools} | tool_mode={tool_mode} | "
        f"vehicle_changed={vehicle_changed} | include_history={include_history} | "
        f"working_vehicle={working_memory.vehicle or '—'} | role={request.user_role()} | "
        f"cita_usuario={'ok' if cita_usuario else 'incompleto/ausente'}"
    )

    return GenerationPlan(
        intent=intent,
        run_rag=run_rag,
        use_tools=use_tools,
        tool_mode=tool_mode,
        include_conversation_history=include_history,
        working_memory=working_memory,
        vehicle_changed=vehicle_changed,
        retrieval_query=retrieval_query,
        conversation_history=conversation_history,
        current_question=current_question,
        user_role=request.user_role(),
        user_profile_text=user_profile_text,
        cita_usuario=cita_usuario,
    )
