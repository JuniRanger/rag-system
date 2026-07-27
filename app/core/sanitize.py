"""Sanitización de inputs para filtros PostgREST / payloads externos.

No hay SQL crudo en este proyecto: las consultas van por el cliente Supabase
(PostgREST). Estas helpers mitigan abuso de ILIKE, identificadores inválidos
y payloads demasiado largos o con caracteres de control.
"""

from __future__ import annotations

import re
from typing import Any

# Identificadores SQL/PostgREST seguros: letra/underscore + alfanuméricos.
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_CITA_FECHA_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

DEFAULT_TEXT_MAX_LEN = 200
DEFAULT_QUERY_MAX_LEN = 4000
DEFAULT_PATH_MAX_LEN = 512
MAX_TOOL_LIMIT = 20
MIN_TOOL_LIMIT = 1


class SanitizeError(ValueError):
    """Input inválido tras sanitización."""


def strip_control_chars(value: str) -> str:
    return _CONTROL_CHARS_RE.sub("", value)


def sanitize_text(
    value: Any,
    *,
    field: str = "value",
    max_length: int = DEFAULT_TEXT_MAX_LEN,
    allow_empty: bool = False,
) -> str:
    """Normaliza texto libre: strip, sin null/control chars, longitud acotada."""
    if value is None:
        text = ""
    else:
        text = str(value)
    text = strip_control_chars(text).strip()
    if not text and not allow_empty:
        raise SanitizeError(f"{field} no puede estar vacío.")
    if len(text) > max_length:
        raise SanitizeError(f"{field} excede el máximo de {max_length} caracteres.")
    return text


def escape_like_pattern(value: str) -> str:
    """Neutraliza comodines LIKE/ILIKE (% y _) para búsqueda literal.

    PostgREST/Postgres no garantiza escape con ``\\`` sin cláusula ESCAPE,
    así que se eliminan los comodines en lugar de escaparlos.
    """
    return value.replace("%", "").replace("_", "")


def ilike_contains(value: Any, *, field: str = "value", max_length: int = DEFAULT_TEXT_MAX_LEN) -> str:
    """Valor seguro para `.ilike(col, pattern)` con contains sin comodines inyectados."""
    cleaned = sanitize_text(value, field=field, max_length=max_length)
    literal = escape_like_pattern(cleaned)
    if not literal:
        raise SanitizeError(f"{field} no puede contener solo comodines.")
    return f"%{literal}%"


def sanitize_identifier(value: Any, *, field: str = "identifier") -> str:
    """Nombre de tabla/columna: solo identificadores SQL seguros."""
    text = sanitize_text(value, field=field, max_length=63)
    if not _IDENTIFIER_RE.fullmatch(text):
        raise SanitizeError(
            f"{field} inválido: solo letras, números y guion bajo; "
            "debe empezar con letra o guion bajo."
        )
    if ".." in text or "/" in text or "\\" in text:
        raise SanitizeError(f"{field} inválido.")
    return text


def sanitize_record_id(value: Any, *, field: str = "record_id") -> str:
    """ID de registro para `.eq`: sin controles, longitud acotada."""
    return sanitize_text(value, field=field, max_length=128)


def clamp_limit(value: Any, *, default: int = 5, minimum: int = MIN_TOOL_LIMIT, maximum: int = MAX_TOOL_LIMIT) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = default
    return max(minimum, min(maximum, limit))


def sanitize_relative_path(value: Any, *, field: str = "path", max_length: int = DEFAULT_PATH_MAX_LEN) -> str:
    """Ruta relativa segura (sin traversal absoluto ni `..`)."""
    text = sanitize_text(value, field=field, max_length=max_length)
    if text.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", text):
        raise SanitizeError(f"{field} debe ser una ruta relativa.")
    parts = re.split(r"[\\/]+", text)
    if any(part == ".." for part in parts):
        raise SanitizeError(f"{field} no puede contener '..'.")
    return text


def sanitize_cita_fecha(value: Any, *, field: str = "fecha") -> str:
    text = sanitize_text(value, field=field, max_length=16)
    if not _CITA_FECHA_RE.fullmatch(text):
        raise SanitizeError(f"{field} debe tener formato YYYY-MM-DD HH:MM.")
    return text
