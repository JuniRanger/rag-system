"""
Ruteo entre RAG (documentos) y Function Calling (herramientas automotrices).

La decisión es heurística por palabras clave: rápida y sin llamadas extra al LLM.
"""
import unicodedata

FUNCTION_KEYWORDS = [

    # Costos
    "costo",
    "precio",
    "cotizacion",
    "presupuesto",

    # Diagnóstico
    "diagnóstico",
    "diagnostico",
    "problema",
    "falla",
    "averia",
    "avería",

    # Historial / servicios
    "historial",
    "servicio",
    "mantenimiento",
    "reparacion",
    "reparación",

    # Componentes
    "componente",
    "motor",
    "frenos",
    "clutch",
    "radiador",
    "bateria",
    "batería",
    "aceite",
    "llantas",
    "transmision",
    "transmisión",
    "coolant",
    "brake",
    "engine",
    "battery",

    # Kilometraje
    "kilometraje",
    "km",

    # Prioridad / severidad
    "severidad",
    "prioridad",

    # Regiones
    "region",
    "región",

    # Predicción
    "predice",
    "prediccion",
    "predicción",

    # Estado
    "estado",
]


def _fold_accents(text: str) -> str:
    """Normaliza a minúsculas y quita tildes para comparar con queries sin acentos."""
    lowered = text.lower()
    return "".join(
            c
            for c in unicodedata.normalize("NFD", lowered)
            if unicodedata.category(c) != "Mn"
        )


def should_use_tools(query: str) -> bool:
    """
    True si la pregunta parece pedir datos de mantenimiento / costos / diagnóstico
    (dominio de las tools CSV), en lugar de lectura de documentos indexados.
    """
    folded = _fold_accents(query)
    return any(_fold_accents(keyword) in folded for keyword in FUNCTION_KEYWORDS)
