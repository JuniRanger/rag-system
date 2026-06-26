import json

from app.core.config import settings
from app.core.supabase import get_supabase_client
from app.tools.base import BaseTool
from app.tools.registry import tool_registry
from app.tools.schemas.supabase import (
    SCHEMA_BUSCAR_CATEGORIA,
    SCHEMA_BUSCAR_CODIGO_ECU,
    SCHEMA_BUSCAR_ESTATUS_TALLER,
    SCHEMA_BUSCAR_SEVERIDAD,
    SCHEMA_BUSCAR_VEHICULO,
    SCHEMA_CONTAR_MARCA,
    SCHEMA_LISTAR_ULTIMOS,
    SCHEMA_OBTENER_ECU,
    SCHEMA_SOLUCION_RAPIDA,
    SCHEMA_VERIFICAR_EXISTENCIA,
)

DEFAULT_LIMIT = 20


def _table():
    return get_supabase_client().table(settings.SUPABASE_TABLE)


def _format_rows(rows: list[dict], header: str) -> str:
    if not rows:
        return f"{header}\nNo se encontraron registros."

    lines = [header, f"Total: {len(rows)} registro(s)."]
    for index, row in enumerate(rows, 1):
        record_id = row.get("id", "N/A")
        summary_parts = []
        for key in (
            "vehiculo_marca",
            "vehiculo_modelo",
            "categoria_problema",
            "problema",
            "diagnostico",
            "solucion",
            "severidad",
            "repair_status",
        ):
            value = row.get(key)
            if value not in (None, ""):
                summary_parts.append(f"{key}: {value}")
        lines.append(f"\n[{index}] id={record_id}")
        lines.extend(summary_parts or [json.dumps(row, ensure_ascii=False, default=str)])
    return "\n".join(lines)


class BuscarPorVehiculoTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_BUSCAR_VEHICULO)

    def run(self, marca: str, modelo: str):
        response = (
            _table()
            .select("*")
            .ilike("vehiculo_marca", f"%{marca}%")
            .ilike("vehiculo_modelo", f"%{modelo}%")
            .limit(DEFAULT_LIMIT)
            .execute()
        )
        return _format_rows(response.data or [], f"Reportes para {marca} {modelo}:")


class BuscarPorCategoriaTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_BUSCAR_CATEGORIA)

    def run(self, categoria: str):
        response = (
            _table()
            .select("*")
            .ilike("categoria_problema", f"%{categoria}%")
            .limit(DEFAULT_LIMIT)
            .execute()
        )
        return _format_rows(response.data or [], f"Casos en categoría '{categoria}':")


class BuscarPorSeveridadTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_BUSCAR_SEVERIDAD)

    def run(self, severidad: str):
        response = (
            _table()
            .select("*")
            .ilike("severidad", f"%{severidad}%")
            .limit(DEFAULT_LIMIT)
            .execute()
        )
        return _format_rows(response.data or [], f"Casos con severidad '{severidad}':")


class BuscarPorEstatusTallerTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_BUSCAR_ESTATUS_TALLER)

    def run(self, estatus: str):
        response = (
            _table()
            .select("*")
            .ilike("repair_status", f"%{estatus}%")
            .limit(DEFAULT_LIMIT)
            .execute()
        )
        return _format_rows(response.data or [], f"Vehículos con estatus '{estatus}':")


class ObtenerDatosEcuTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_OBTENER_ECU)

    def run(self, record_id: str):
        response = (
            _table()
            .select("id, ecu_data, vehiculo_marca, vehiculo_modelo")
            .eq("id", record_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return f"No se encontró el registro con id={record_id}."
        row = rows[0]
        return (
            f"ECU del registro {record_id} "
            f"({row.get('vehiculo_marca')} {row.get('vehiculo_modelo')}):\n"
            f"{row.get('ecu_data', 'Sin datos ECU')}"
        )


class BuscarPorCodigoErrorEcuTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_BUSCAR_CODIGO_ECU)

    def run(self, codigo_error: str):
        response = (
            _table()
            .select("*")
            .ilike("ecu_data", f"%{codigo_error}%")
            .limit(DEFAULT_LIMIT)
            .execute()
        )
        return _format_rows(
            response.data or [],
            f"Registros con código ECU '{codigo_error}':",
        )


class ObtenerSolucionRapidaTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_SOLUCION_RAPIDA)

    def run(self, record_id: str):
        response = (
            _table()
            .select("id, diagnostico, solucion, problema, vehiculo_marca, vehiculo_modelo")
            .eq("id", record_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return f"No se encontró el registro con id={record_id}."
        row = rows[0]
        return (
            f"Resumen rápido id={record_id} "
            f"({row.get('vehiculo_marca')} {row.get('vehiculo_modelo')}):\n"
            f"Problema: {row.get('problema', 'N/A')}\n"
            f"Diagnóstico: {row.get('diagnostico', 'N/A')}\n"
            f"Solución: {row.get('solucion', 'N/A')}"
        )


class ContarCasosPorMarcaTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_CONTAR_MARCA)

    def run(self, marca: str):
        response = (
            _table()
            .select("id", count="exact")
            .ilike("vehiculo_marca", f"%{marca}%")
            .execute()
        )
        total = response.count if response.count is not None else len(response.data or [])
        return f"Total de incidencias para la marca '{marca}': {total} caso(s)."


class ListarUltimosReportesTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_LISTAR_ULTIMOS)

    def run(self, limite: int = 5):
        response = (
            _table()
            .select("*")
            .order("created_at", desc=True)
            .limit(limite)
            .execute()
        )
        return _format_rows(response.data or [], f"Últimos {limite} reportes:")


class VerificarExistenciaVehiculoTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_VERIFICAR_EXISTENCIA)

    def run(self, marca: str, modelo: str):
        response = (
            _table()
            .select("id")
            .ilike("vehiculo_marca", f"%{marca}%")
            .ilike("vehiculo_modelo", f"%{modelo}%")
            .limit(1)
            .execute()
        )
        exists = bool(response.data)
        if exists:
            return f"El vehículo {marca} {modelo} ya tiene historial en el sistema (id={response.data[0]['id']})."
        return f"No hay registros previos para {marca} {modelo}."


def register_read_tools() -> None:
    for tool in (
        BuscarPorVehiculoTool(),
        BuscarPorCategoriaTool(),
        BuscarPorSeveridadTool(),
        BuscarPorEstatusTallerTool(),
        ObtenerDatosEcuTool(),
        BuscarPorCodigoErrorEcuTool(),
        ObtenerSolucionRapidaTool(),
        ContarCasosPorMarcaTool(),
        ListarUltimosReportesTool(),
        VerificarExistenciaVehiculoTool(),
    ):
        if tool_registry.get_tool(tool.name) is None:
            tool_registry.register(tool)
