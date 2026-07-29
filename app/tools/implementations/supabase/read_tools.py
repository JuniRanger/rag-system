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
# Máximo de casos que se pasan al LLM (evita dumps masivos de la BD).
MAX_CASES_FOR_LLM = 3

# Campos mínimos útiles para diagnóstico (sin IDs ni schema de BD).
_SAFE_CASE_FIELDS = (
    ("problema", "Problema"),
    ("diagnostico", "Diagnóstico"),
    ("solucion", "Solución"),
)


def _table():
    return get_supabase_client().table(settings.SUPABASE_TABLE)


def _format_case_for_llm(row: dict, index: int) -> list[str]:
    """Proyecta un registro a texto mínimo para el LLM (sin IDs ni metadata)."""
    lines = [f"Caso {index}:"]
    vehicle_parts = [
        str(row.get("vehiculo_marca") or "").strip(),
        str(row.get("vehiculo_modelo") or "").strip(),
    ]
    vehicle = " ".join(part for part in vehicle_parts if part)
    if vehicle:
        lines.append(f"Vehículo: {vehicle}")

    for key, label in _SAFE_CASE_FIELDS:
        value = row.get(key)
        if value not in (None, ""):
            lines.append(f"{label}: {value}")

    if len(lines) == 1:
        lines.append("(sin detalle clínico útil en el registro)")
    return lines


def _format_rows(rows: list[dict], header: str) -> str:
    if not rows:
        return f"{header}\nNo se encontraron casos relevantes."

    limited = rows[:MAX_CASES_FOR_LLM]
    lines = [
        header,
        f"Se muestran {len(limited)} caso(s) relevantes"
        + (f" de {len(rows)} encontrados." if len(rows) > len(limited) else "."),
        "Usa solo problema, diagnóstico y solución. No menciones IDs ni estructura interna.",
    ]
    for index, row in enumerate(limited, 1):
        lines.append("")
        lines.extend(_format_case_for_llm(row, index))
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
