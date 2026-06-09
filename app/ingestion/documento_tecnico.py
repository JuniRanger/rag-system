"""Utilidades para rag.documentos_tecnicos -> texto indexable."""
from typing import Any

from app.api.schemas import DocumentoTecnicoRecordSchema


def parse_documento_tecnico(record: dict[str, Any]) -> DocumentoTecnicoRecordSchema:
    return DocumentoTecnicoRecordSchema.model_validate(record)


def documento_tecnico_to_text(record: dict[str, Any]) -> str:
    doc = parse_documento_tecnico(record)
    sections: list[str] = []

    vehiculo = " ".join(
        p for p in (doc.vehiculo_marca, doc.vehiculo_modelo) if p
    ).strip()
    if vehiculo:
        sections.append(f"Vehiculo: {vehiculo}")

    labeled = [
        ("Categoria", doc.categoria_problema),
        ("Problema", doc.problema),
        ("Diagnostico", doc.diagnostico),
        ("Solucion", doc.solucion),
        ("ECU", doc.ecu_data),
        ("Severidad", doc.severidad),
        ("Estado reparacion", doc.repair_status),
        ("Historial servicio", doc.historial_servicio),
    ]
    for label, value in labeled:
        if value and str(value).strip():
            sections.append(f"{label}: {str(value).strip()}")

    return "\n".join(sections)


def documento_tecnico_metadata(record: dict[str, Any]) -> dict[str, Any]:
    doc = parse_documento_tecnico(record)
    return {
        k: v
        for k, v in {
            "vehiculo_marca": doc.vehiculo_marca,
            "vehiculo_modelo": doc.vehiculo_modelo,
            "categoria_problema": doc.categoria_problema,
            "problema": doc.problema,
            "diagnostico": doc.diagnostico,
            "solucion": doc.solucion,
            "severidad": doc.severidad,
            "repair_status": doc.repair_status,
        }.items()
        if v is not None and str(v).strip()
    }
