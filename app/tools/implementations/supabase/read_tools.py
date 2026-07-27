import json

from app.core.config import settings
from app.core.sanitize import (
    SanitizeError,
    clamp_limit,
    ilike_contains,
    sanitize_record_id,
    sanitize_text,
)
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
        lines.append(f"\n[{index}]")
        if summary_parts:
            lines.extend(summary_parts)
        else:
            # Sin volcar id ni claves internas crudas.
            safe_row = {
                k: v
                for k, v in row.items()
                if str(k).lower() != "id" and not str(k).lower().endswith("_id")
            }
            lines.append(json.dumps(safe_row, ensure_ascii=False, default=str))
    return "\n".join(lines)


def _invalid_arg(error: SanitizeError) -> str:
    return f"Argumento inválido: {error}"


class BuscarPorVehiculoTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_BUSCAR_VEHICULO)

    def run(self, marca: str, modelo: str):
        try:
            marca_clean = sanitize_text(marca, field="marca")
            modelo_clean = sanitize_text(modelo, field="modelo")
            marca_pat = ilike_contains(marca_clean, field="marca")
            modelo_pat = ilike_contains(modelo_clean, field="modelo")
        except SanitizeError as error:
            return _invalid_arg(error)

        response = (
            _table()
            .select("*")
            .ilike("vehiculo_marca", marca_pat)
            .ilike("vehiculo_modelo", modelo_pat)
            .limit(DEFAULT_LIMIT)
            .execute()
        )
        return _format_rows(response.data or [], f"Reportes para {marca_clean} {modelo_clean}:")


class BuscarPorCategoriaTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_BUSCAR_CATEGORIA)

    def run(self, categoria: str):
        try:
            categoria_clean = sanitize_text(categoria, field="categoria")
            pattern = ilike_contains(categoria_clean, field="categoria")
        except SanitizeError as error:
            return _invalid_arg(error)

        response = (
            _table()
            .select("*")
            .ilike("categoria_problema", pattern)
            .limit(DEFAULT_LIMIT)
            .execute()
        )
        return _format_rows(response.data or [], f"Casos en categoría '{categoria_clean}':")


class BuscarPorSeveridadTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_BUSCAR_SEVERIDAD)

    def run(self, severidad: str):
        try:
            severidad_clean = sanitize_text(severidad, field="severidad")
            pattern = ilike_contains(severidad_clean, field="severidad")
        except SanitizeError as error:
            return _invalid_arg(error)

        response = (
            _table()
            .select("*")
            .ilike("severidad", pattern)
            .limit(DEFAULT_LIMIT)
            .execute()
        )
        return _format_rows(response.data or [], f"Casos con severidad '{severidad_clean}':")


class BuscarPorEstatusTallerTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_BUSCAR_ESTATUS_TALLER)

    def run(self, estatus: str):
        try:
            estatus_clean = sanitize_text(estatus, field="estatus")
            pattern = ilike_contains(estatus_clean, field="estatus")
        except SanitizeError as error:
            return _invalid_arg(error)

        response = (
            _table()
            .select("*")
            .ilike("repair_status", pattern)
            .limit(DEFAULT_LIMIT)
            .execute()
        )
        return _format_rows(response.data or [], f"Vehículos con estatus '{estatus_clean}':")


class ObtenerDatosEcuTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_OBTENER_ECU)

    def run(self, record_id: str):
        try:
            safe_id = sanitize_record_id(record_id)
        except SanitizeError as error:
            return _invalid_arg(error)

        response = (
            _table()
            .select("id, ecu_data, vehiculo_marca, vehiculo_modelo")
            .eq("id", safe_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return "No se encontró el registro solicitado."
        row = rows[0]
        return (
            f"Datos ECU "
            f"({row.get('vehiculo_marca')} {row.get('vehiculo_modelo')}):\n"
            f"{row.get('ecu_data', 'Sin datos ECU')}"
        )


class BuscarPorCodigoErrorEcuTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_BUSCAR_CODIGO_ECU)

    def run(self, codigo_error: str):
        try:
            codigo_clean = sanitize_text(codigo_error, field="codigo_error", max_length=64)
            pattern = ilike_contains(codigo_clean, field="codigo_error", max_length=64)
        except SanitizeError as error:
            return _invalid_arg(error)

        response = (
            _table()
            .select("*")
            .ilike("ecu_data", pattern)
            .limit(DEFAULT_LIMIT)
            .execute()
        )
        return _format_rows(
            response.data or [],
            f"Registros con código ECU '{codigo_clean}':",
        )


class ObtenerSolucionRapidaTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_SOLUCION_RAPIDA)

    def run(self, record_id: str):
        try:
            safe_id = sanitize_record_id(record_id)
        except SanitizeError as error:
            return _invalid_arg(error)

        response = (
            _table()
            .select("id, diagnostico, solucion, problema, vehiculo_marca, vehiculo_modelo")
            .eq("id", safe_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return "No se encontró el registro solicitado."
        row = rows[0]
        return (
            f"Resumen rápido "
            f"({row.get('vehiculo_marca')} {row.get('vehiculo_modelo')}):\n"
            f"Problema: {row.get('problema', 'N/A')}\n"
            f"Diagnóstico: {row.get('diagnostico', 'N/A')}\n"
            f"Solución: {row.get('solucion', 'N/A')}"
        )


class ContarCasosPorMarcaTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_CONTAR_MARCA)

    def run(self, marca: str):
        try:
            marca_clean = sanitize_text(marca, field="marca")
            pattern = ilike_contains(marca_clean, field="marca")
        except SanitizeError as error:
            return _invalid_arg(error)

        response = (
            _table()
            .select("id", count="exact")
            .ilike("vehiculo_marca", pattern)
            .execute()
        )
        total = response.count if response.count is not None else len(response.data or [])
        return f"Total de incidencias para la marca '{marca_clean}': {total} caso(s)."


class ListarUltimosReportesTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_LISTAR_ULTIMOS)

    def run(self, limite: int = 5):
        safe_limit = clamp_limit(limite, default=5)
        response = (
            _table()
            .select("*")
            .order("created_at", desc=True)
            .limit(safe_limit)
            .execute()
        )
        return _format_rows(response.data or [], f"Últimos {safe_limit} reportes:")


class VerificarExistenciaVehiculoTool(BaseTool):
    def __init__(self):
        super().__init__(SCHEMA_VERIFICAR_EXISTENCIA)

    def run(self, marca: str, modelo: str):
        try:
            marca_clean = sanitize_text(marca, field="marca")
            modelo_clean = sanitize_text(modelo, field="modelo")
            marca_pat = ilike_contains(marca_clean, field="marca")
            modelo_pat = ilike_contains(modelo_clean, field="modelo")
        except SanitizeError as error:
            return _invalid_arg(error)

        response = (
            _table()
            .select("id")
            .ilike("vehiculo_marca", marca_pat)
            .ilike("vehiculo_modelo", modelo_pat)
            .limit(1)
            .execute()
        )
        exists = bool(response.data)
        if exists:
            return f"El vehículo {marca_clean} {modelo_clean} ya tiene historial en el sistema."
        return f"No hay registros previos para {marca_clean} {modelo_clean}."


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
