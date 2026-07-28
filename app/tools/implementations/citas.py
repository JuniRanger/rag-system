"""Herramientas de agendamiento de citas vía API externa."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.logger import logger
from app.core.sanitize import SanitizeError, sanitize_cita_fecha, sanitize_text
from app.services.api_client import InternalApiError, get_api_client
from app.tools.base import BaseTool
from app.tools.registry import tool_registry
from app.tools.schemas.citas import SCHEMA_CREAR_CITA

CITAS_AGENDAR_PATH = "/citas/agendar"

# Campos que el LLM puede usar al confirmar al usuario (nunca IDs).
_SAFE_CITA_FIELDS = frozenset({"fecha", "vehiculo", "producto", "mensaje", "message", "status"})


def _sanitize_api_body_for_llm(body: Any) -> str:
    """Resume la respuesta del backend sin IDs ni metadata de registros."""
    if isinstance(body, dict):
        safe = {
            key: value
            for key, value in body.items()
            if key.lower() in _SAFE_CITA_FIELDS
            and not str(key).lower().endswith("id")
            and str(key).lower() != "id"
        }
        if safe:
            return str(safe)
        return "operación procesada"
    if isinstance(body, str):
        # Evitar reenviar JSON crudo con ids al modelo.
        stripped = body.strip()
        if stripped.startswith("{") or '"id"' in stripped.lower():
            return "detalle interno omitido"
        return stripped[:200]
    return "detalle interno omitido"


def _normalize_usuario(usuario: Any) -> dict[str, str] | None:
    """Normaliza el objeto usuario al DTO de la API de citas."""
    if not isinstance(usuario, dict):
        return None

    try:
        user_id = sanitize_text(usuario.get("id"), field="usuario.id", max_length=128)
        nombre = sanitize_text(usuario.get("nombre"), field="usuario.nombre", max_length=120)
        correo = sanitize_text(
            usuario.get("correo") or usuario.get("email"),
            field="usuario.correo",
            max_length=254,
        )
    except SanitizeError:
        return None

    return {
        "id": user_id,
        "nombre": nombre,
        "correo": correo,
    }


class CrearCitaAPITool(BaseTool):
    def __init__(self) -> None:
        super().__init__(SCHEMA_CREAR_CITA)

    async def run(
        self,
        fecha: str,
        vehiculo: str,
        producto: str,
        usuario: dict | None = None,
    ) -> str:
        """
        Agenda una cita con el DTO:

        {
          "fecha": "YYYY-MM-DD HH:MM",
          "vehiculo": "...",
          "producto": "...",
          "usuario": {"id": "...", "nombre": "...", "correo": "..."}
        }
        """
        logger.info(
            "crearCitaAPI recibido:\n"
            f"fecha={fecha!r}\n"
            f"vehiculo={vehiculo!r}\n"
            f"producto={producto!r}"
        )
        base_url = (settings.CITAS_API_BASE_URL or "").rstrip("/")
        if not base_url:
            return (
                "Error: CITAS_API_BASE_URL no está configurada. "
                "No se pudo agendar la cita."
            )

        usuario_payload = _normalize_usuario(usuario)
        if usuario_payload is None:
            return (
                "Error: faltan datos del cliente en el request "
                "(user.id + user.usuario.nombre + user.usuario.correo/email). "
                "No se puede agendar la cita."
            )

        try:
            fecha_norm = sanitize_cita_fecha(fecha)
            vehiculo_norm = sanitize_text(vehiculo, field="vehiculo", max_length=120)
            producto_norm = sanitize_text(producto, field="producto", max_length=120)
        except SanitizeError as error:
            return f"Error: {error}"

        payload = {
            "fecha": fecha_norm,
            "vehiculo": vehiculo_norm,
            "producto": producto_norm,
            "usuario": usuario_payload,
        }

        logger.info(
            "API PAYLOAD:\n"
            f"fecha={payload['fecha']!r}\n"
            f"vehiculo={payload['vehiculo']!r}\n"
            f"producto={payload['producto']!r}\n"
            f"usuario={payload['usuario']!r}\n"
            f"POST {base_url}{CITAS_AGENDAR_PATH}"
        )

        try:
            api_client = get_api_client(base_url=base_url)
            response = await api_client.post(CITAS_AGENDAR_PATH, json=payload)

            try:
                body = response.json()
            except Exception:
                body = response.text

            logger.info(f"crearCitaAPI respuesta HTTP {response.status_code}")

            if response.is_success:
                return (
                    "Cita agendada correctamente. "
                    f"Confirma al usuario: fecha={fecha_norm}, "
                    f"vehiculo={vehiculo_norm}, producto={producto_norm}. "
                    "No menciones IDs, UUIDs ni identificadores de ningún registro."
                )

            safe_detail = _sanitize_api_body_for_llm(body)
            return (
                "Error al agendar la cita. "
                f"Informa al usuario de forma natural sin datos internos. "
                f"Detalle seguro: {safe_detail}"
            )
        except InternalApiError as error:
            logger.error(
                f"crearCitaAPI: {error.error_type}"
                + (f" status={error.status_code}" if error.status_code else "")
            )
            return f"Error: {error}"


def register_cita_tools() -> None:
    tool = CrearCitaAPITool()
    if tool_registry.get_tool(tool.name) is None:
        tool_registry.register(tool)
