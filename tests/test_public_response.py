from app.rag.mappers import to_public_payload, to_public_response
from app.rag.schemas import (
    FunctionCallRecord,
    PublicRAGResponse,
    RAGResponse,
    RAGResponseMetadata,
    SourceReference,
    WorkingMemory,
)
from app.tools.implementations.supabase.read_tools import _format_rows


def _sample_internal_response() -> RAGResponse:
    return RAGResponse(
        success=True,
        conversation_id="conv-1",
        answer="Cambia las balatas delanteras.",
        summary="Cliente consulta balatas.",
        working_memory=WorkingMemory(vehicle="Mazda 3", problem="balatas"),
        sources=[
            SourceReference(document_id="99", score=0.91, label="tabla#99"),
        ],
        metadata=RAGResponseMetadata(
            latency_ms=123,
            ttft_ms=40,
            tokens_per_second=12.5,
            intent="automotive",
            vehicle_changed=True,
            rag_executed=True,
            retrieved_chunks=8,
            used_chunks=3,
            tokens_input=400,
            tokens_output=50,
            tools_used=[
                FunctionCallRecord(
                    name="buscar_por_severidad",
                    arguments={"severidad": "alta"},
                    status="success",
                    output="id=42 diagnostico secreto",
                )
            ],
            function_calls=[
                FunctionCallRecord(
                    name="buscar_por_severidad",
                    arguments={"severidad": "alta"},
                    status="success",
                    output="id=42 diagnostico secreto",
                )
            ],
            context_used=[{"text": "secreto", "metadata": {"record_id": 42}}],
        ),
    )


def test_public_response_strips_internal_metadata():
    public = to_public_response(_sample_internal_response())
    assert isinstance(public, PublicRAGResponse)
    payload = public.model_dump()

    assert set(payload.keys()) == {
        "success",
        "conversation_id",
        "answer",
        "working_memory",
    }
    assert "metadata" not in payload
    assert "sources" not in payload
    assert "summary" not in payload
    assert "tools_used" not in payload
    assert "tokens_input" not in payload
    assert payload["answer"] == "Cambia las balatas delanteras."
    assert payload["working_memory"]["vehicle"] == "Mazda 3"


def test_public_payload_has_no_tool_or_token_leakage():
    raw = str(to_public_payload(_sample_internal_response()))
    for forbidden in (
        "buscar_por_severidad",
        "tokens_input",
        "latency_ms",
        "record_id",
        "id=42",
        "context_used",
        "function_calls",
        "Cliente consulta balatas",  # summary interno
    ):
        assert forbidden not in raw


def test_format_rows_exposes_only_clinical_fields():
    rows = [
        {
            "id": 1,
            "vehiculo_marca": "Hyundai",
            "vehiculo_modelo": "Santa Fe",
            "problema": "No arranca",
            "diagnostico": "Batería débil",
            "solucion": "Reemplazar batería",
            "severidad": "alta",
            "repair_status": "pendiente",
            "categoria_problema": "electrico",
            "created_at": "2026-01-01",
        },
        {
            "id": 2,
            "problema": "Ruido",
            "diagnostico": "Balatas",
            "solucion": "Cambio",
        },
        {
            "id": 3,
            "problema": "Vibración",
            "diagnostico": "Rines",
            "solucion": "Balanceo",
        },
        {
            "id": 4,
            "problema": "Extra",
            "diagnostico": "No debe aparecer",
            "solucion": "No debe aparecer",
        },
    ]
    text = _format_rows(rows, "Resultados de prueba:")
    assert "Problema: No arranca" in text
    assert "Diagnóstico: Batería débil" in text
    assert "Solución: Reemplazar batería" in text
    assert "Hyundai Santa Fe" in text
    assert "id=" not in text.lower()
    assert '"id"' not in text.lower()
    assert "severidad" not in text
    assert "repair_status" not in text
    assert "categoria_problema" not in text
    assert "created_at" not in text
    assert "No debe aparecer" not in text  # 4º caso truncado
    assert "3 caso" in text
