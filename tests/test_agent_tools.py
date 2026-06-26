import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest

from app.llm.ollama_client import get_ollama_base_url
from app.rag.tool_loop import _parse_tool_arguments, run_tool_augmented_generation
from app.tools.executor import tool_executor
from app.tools.implementations.supabase.read_tools import register_read_tools
from app.tools.registry import tool_registry

SAMPLE_ROWS = [
    {
        "id": "uuid-1",
        "vehiculo_marca": "Hyundai",
        "vehiculo_modelo": "Santa Fe 2016",
        "categoria_problema": "Battery",
        "problema": "No enciende",
        "diagnostico": "Batería descargada",
        "solucion": "Cargar sistema",
        "severidad": "Alta",
        "repair_status": "En progreso",
        "ecu_data": "ERROR_CODE: 404_RIZZ",
        "created_at": "2026-01-01T10:00:00Z",
    },
    {
        "id": "uuid-2",
        "vehiculo_marca": "Tesla",
        "vehiculo_modelo": "Model 3",
        "categoria_problema": "Electrical",
        "problema": "Pantalla apagada",
        "diagnostico": "Fusible quemado",
        "solucion": "Reemplazar fusible",
        "severidad": "Media",
        "repair_status": "Terminado",
        "ecu_data": "OK",
        "created_at": "2026-01-02T10:00:00Z",
    },
]


class FakeQuery:
    def __init__(self, rows: list[dict]):
        self._rows = rows
        self._filters: list[tuple] = []
        self._order: tuple | None = None
        self._limit: int | None = None
        self._count: str | None = None

    def select(self, *columns, count=None):
        self._count = count
        return self

    def ilike(self, column: str, pattern: str):
        needle = pattern.strip("%").lower()
        self._filters.append(("ilike", column, needle))
        return self

    def eq(self, column: str, value):
        self._filters.append(("eq", column, value))
        return self

    def gt(self, column: str, value):
        self._filters.append(("gt", column, value))
        return self

    def order(self, column: str, desc: bool = False):
        self._order = (column, desc)
        return self

    def limit(self, value: int):
        self._limit = value
        return self

    def range(self, start: int, end: int):
        self._offset = start
        self._limit = end - start + 1
        return self

    def single(self):
        self._limit = 1
        return self

    def _apply_filters(self, rows: list[dict]) -> list[dict]:
        filtered = rows
        for filter_type, column, value in self._filters:
            if filter_type == "ilike":
                filtered = [
                    row
                    for row in filtered
                    if value in str(row.get(column, "")).lower()
                ]
            elif filter_type == "eq":
                filtered = [row for row in filtered if row.get(column) == value]
            elif filter_type == "gt":
                filtered = [row for row in filtered if row.get(column) > value]
        return filtered

    def execute(self):
        rows = self._apply_filters(self._rows)

        if self._order:
            column, desc = self._order
            rows = sorted(rows, key=lambda row: row.get(column), reverse=desc)

        if self._limit is not None:
            offset = getattr(self, "_offset", 0)
            rows = rows[offset : offset + self._limit]

        if self._count == "exact":
            return SimpleNamespace(data=rows, count=len(rows))
        return SimpleNamespace(data=rows, count=len(rows))


class FakeSupabaseClient:
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def table(self, _name: str):
        return FakeQuery(self._rows)


class MockLLMProvider:
    def __init__(self):
        self.calls = 0

    def chat_with_tools(self, messages, tools, options=None):
        self.calls += 1
        if self.calls == 1:
            return {
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "name": "buscar_por_vehiculo",
                            "arguments": {
                                "marca": "Hyundai",
                                "modelo": "Santa Fe",
                            },
                        }
                    }
                ],
            }
        return {
            "role": "assistant",
            "content": "Hay un reporte de batería descargada para ese vehículo.",
        }

    async def chat_with_tools_async(self, messages, tools, options=None):
        return self.chat_with_tools(messages, tools, options)


@pytest.fixture(autouse=True)
def reset_tool_registry():
    tool_registry._tools.clear()
    yield
    tool_registry._tools.clear()


@pytest.fixture
def registered_tools():
    with patch(
        "app.tools.implementations.supabase.read_tools.get_supabase_client",
        return_value=FakeSupabaseClient(SAMPLE_ROWS),
    ):
        register_read_tools()
        yield


def test_register_read_tools_exposes_ollama_schemas(registered_tools):
    names = tool_registry.list_tool_names()

    assert "buscar_por_vehiculo" in names
    assert "contar_casos_por_marca" in names
    assert len(tool_registry.get_ollama_schemas()) == 10


def test_executor_buscar_por_vehiculo(registered_tools):
    result = tool_executor.execute(
        "buscar_por_vehiculo",
        {"marca": "Hyundai", "modelo": "Santa Fe"},
    )

    assert result["status"] == "success"
    assert "Hyundai" in result["output"]
    assert "Santa Fe" in result["output"]


def test_executor_contar_casos_por_marca(registered_tools):
    result = tool_executor.execute("contar_casos_por_marca", {"marca": "Tesla"})

    assert result["status"] == "success"
    assert "1 caso" in result["output"]


def test_executor_unknown_tool_returns_error():
    result = tool_executor.execute("herramienta_inexistente", {})

    assert result["status"] == "error"
    assert "no existe" in result["output"]


def test_parse_tool_arguments_accepts_dict_and_json_string():
    assert _parse_tool_arguments({"marca": "Hyundai"}) == {"marca": "Hyundai"}
    assert _parse_tool_arguments('{"marca": "Tesla"}') == {"marca": "Tesla"}
    assert _parse_tool_arguments("") == {}


def test_run_tool_augmented_generation_executes_tool_and_returns_answer(registered_tools):
    result = asyncio.run(
        run_tool_augmented_generation(
            llm_provider=MockLLMProvider(),
            query="¿Hay reportes para un Hyundai Santa Fe 2016?",
            context_text="[Fragmento 1] Contexto semántico de prueba.",
        )
    )

    assert result["tools_used"][0]["tool"] == "buscar_por_vehiculo"
    assert result["tools_used"][0]["status"] == "success"
    assert "batería" in result["answer"].lower()


@pytest.mark.integration
def test_ollama_tool_calling_live(registered_tools):
    payload = {
        "model": "llama3.2:1b",
        "messages": [
            {
                "role": "user",
                "content": (
                    "¿Hay reportes de fallas para un Hyundai Santa Fe 2016? "
                    "Usa herramientas si hace falta."
                ),
            }
        ],
        "tools": tool_registry.get_ollama_schemas(),
        "stream": False,
    }

    ollama_chat_url = f"{get_ollama_base_url()}/api/chat"

    try:
        response = httpx.post(
            ollama_chat_url,
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()
    except httpx.ConnectError:
        pytest.skip(f"Ollama no está disponible en {get_ollama_base_url()}")

    message = response.json().get("message", {})
    tool_calls = message.get("tool_calls", [])

    if not tool_calls:
        pytest.skip("El modelo no invocó herramientas en esta ejecución")

    call = tool_calls[0]
    tool_name = call["function"]["name"]
    arguments = call["function"].get("arguments", {})

    if isinstance(arguments, str):
        arguments = json.loads(arguments)

    execution = tool_executor.execute(tool_name, arguments)
    assert execution["status"] == "success"
