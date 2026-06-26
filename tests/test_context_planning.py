from app.rag.context_plan import plan_request
from app.rag.intent import QueryIntent, detect_intent
from app.rag.schemas import ChatMessage, RAGRequest, WorkingMemory
from app.rag.vehicle import extract_vehicle, vehicles_are_different


def test_detect_conversation_intent():
    assert detect_intent("Hola, qué haces", WorkingMemory()) == QueryIntent.CONVERSATION


def test_detect_memory_request_intent():
    assert detect_intent("¿Qué me preguntaste hace rato?", WorkingMemory()) == QueryIntent.MEMORY_REQUEST


def test_detect_automotive_intent():
    assert (
        detect_intent("Tengo una Hyundai con fallo de transmisión", WorkingMemory())
        == QueryIntent.AUTOMOTIVE
    )


def test_vague_opinion_without_active_context_is_conversation():
    assert detect_intent("¿Qué opinas?", WorkingMemory()) == QueryIntent.CONVERSATION


def test_vehicle_change_resets_working_memory():
    request = RAGRequest(
        working_memory=WorkingMemory(vehicle="hyundai santa fe 2016", problem="transmisión"),
        message=ChatMessage(role="user", content="Tengo un Tesla Model S 2019"),
    )
    plan = plan_request(request)

    assert plan.vehicle_changed is True
    assert plan.working_memory.vehicle == "tesla model s 2019"
    assert plan.working_memory.problem == ""


def test_conversation_skips_rag_and_history():
    request = RAGRequest(
        summary="El usuario es un mecánico revisando un Hyundai.",
        recent_messages=[
            ChatMessage(role="user", content="Hyundai con fallo"),
            ChatMessage(role="assistant", content="Cuéntame más"),
        ],
        message=ChatMessage(role="user", content="Hola"),
    )
    plan = plan_request(request)

    assert plan.intent == QueryIntent.CONVERSATION
    assert plan.run_rag is False
    assert plan.conversation_history == ""


def test_memory_request_uses_history_not_summary_in_prompt():
    request = RAGRequest(
        summary="Resumen que no debe ir al prompt.",
        recent_messages=[
            ChatMessage(role="user", content="Pregunta anterior sobre frenos"),
            ChatMessage(role="assistant", content="Revisemos las balatas"),
        ],
        message=ChatMessage(role="user", content="¿Qué acabamos de hablar?"),
    )
    plan = plan_request(request)

    assert plan.intent == QueryIntent.MEMORY_REQUEST
    assert plan.run_rag is False
    assert "Pregunta anterior sobre frenos" in plan.conversation_history
    assert "Resumen que no debe ir" not in plan.conversation_history


def test_automotive_retrieval_uses_working_memory_not_global_summary():
    request = RAGRequest(
        summary="Se discutió un Ford Focus en otra sesión.",
        working_memory=WorkingMemory(vehicle="hyundai santa fe 2016", problem="fallo transmisión"),
        message=ChatMessage(
            role="user",
            content="¿Existen boletines sobre software de transmisión?",
        ),
    )
    plan = plan_request(request)

    assert plan.run_rag is True
    assert "hyundai santa fe 2016" in plan.retrieval_query
    assert "Ford Focus" not in plan.retrieval_query
    assert plan.conversation_history == ""


def test_extract_vehicle_with_year():
    assert extract_vehicle("Hyundai Santa Fe 2016 con ruidos") == "hyundai santa fe 2016"


def test_vehicles_are_different_for_distinct_models():
    assert vehicles_are_different("tesla model s 2019", "hyundai santa fe 2016") is True
