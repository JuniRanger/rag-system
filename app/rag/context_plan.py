from dataclasses import dataclass

from app.rag.intent import QueryIntent, detect_intent, has_explicit_reference
from app.rag.schemas import ChatMessage, RAGRequest, WorkingMemory
from app.rag.vehicle import extract_problem, extract_vehicle, vehicles_are_different
from app.core.logger import logger


@dataclass(frozen=True)
class GenerationPlan:
    intent: QueryIntent
    run_rag: bool
    include_conversation_history: bool
    working_memory: WorkingMemory
    vehicle_changed: bool
    retrieval_query: str
    conversation_history: str
    current_question: str


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
    intent = detect_intent(message, previous_memory)

    detected_vehicle = extract_vehicle(message)
    vehicle_changed = vehicles_are_different(detected_vehicle, previous_memory.vehicle)

    working_memory = _update_working_memory(
        previous=previous_memory,
        message=message,
        intent=intent,
        detected_vehicle=detected_vehicle,
        vehicle_changed=vehicle_changed,
    )

    run_rag = intent == QueryIntent.AUTOMOTIVE

    include_history = intent == QueryIntent.MEMORY_REQUEST or (
        intent == QueryIntent.AUTOMOTIVE and has_explicit_reference(message)
    )

    conversation_history = _format_recent_messages(request.recent_messages) if include_history else ""

    retrieval_query = _build_retrieval_query(working_memory, message) if run_rag else message

    logger.info(
        f"Plan generado | intent={intent.value} | run_rag={run_rag} | "
        f"vehicle_changed={vehicle_changed} | include_history={include_history} | "
        f"working_vehicle={working_memory.vehicle or '—'}"
    )

    return GenerationPlan(
        intent=intent,
        run_rag=run_rag,
        include_conversation_history=include_history,
        working_memory=working_memory,
        vehicle_changed=vehicle_changed,
        retrieval_query=retrieval_query,
        conversation_history=conversation_history,
        current_question=message,
    )
