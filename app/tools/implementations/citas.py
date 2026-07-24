"""Herramientas de agendamiento de citas vía API externa."""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.core.logger import logger
from app.tools.base import BaseTool
from app.tools.registry import tool_registry
from app.tools.schemas.citas import SCHEMA_CREAR_CITA

CITAS_AGENDAR_PATH = "/citas/agendar"
REQUEST_TIMEOUT_SECONDS = 30.0


def _normalize_usuario(usuario: Any) -> dict[str, str] | None:
    """Normaliza el objeto usuario al DTO de la API de citas."""
    if not isinstance(usuario, dict):
        return None

    user_id = str(usuario.get("id") or "").strip()
    nombre = str(usuario.get("nombre") or "").strip()
    correo = str(usuario.get("correo") or usuario.get("email") or "").strip()

    if not user_id or not nombre or not correo:
        return None

    return {
        "id": user_id,
        "nombre": nombre,
        "correo": correo,
    }


class CrearCitaAPITool(BaseTool):
    def __init__(self) -> None:
        super().__init__(SCHEMA_CREAR_CITA)

    def run(
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

        fecha_norm = (fecha or "").strip()
        vehiculo_norm = (vehiculo or "").strip()
        producto_norm = (producto or "").strip()
        if not fecha_norm or not vehiculo_norm or not producto_norm:
            return "Error: fecha, vehiculo y producto son obligatorios."

        url = f"{base_url}{CITAS_AGENDAR_PATH}"
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
            f"POST {url}"
        )

        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = client.post(url, json=payload)

            try:
                body = response.json()
            except Exception:
                body = response.text

            if response.is_success:
                return (
                    f"Cita agendada correctamente (HTTP {response.status_code}). "
                    f"Respuesta del servidor: {body}"
                )

            return (
                f"Error al agendar la cita (HTTP {response.status_code}). "
                f"Detalle: {body}"
            )
        except httpx.TimeoutException:
            logger.error("crearCitaAPI: timeout al contactar la API de citas")
            return "Error: la API de citas no respondió a tiempo. Intenta de nuevo."
        except httpx.HTTPError as error:
            logger.error(f"crearCitaAPI: error HTTP {error}")
            return f"Error de red al agendar la cita: {error}"


def register_cita_tools() -> None:
    tool = CrearCitaAPITool()
    if tool_registry.get_tool(tool.name) is None:
        tool_registry.register(tool)
