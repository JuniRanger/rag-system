FUNCTION_KEYWORDS = [
    "costo",
    "precio",
    "diagnóstico",
    "problema",
    "historial",
    "servicio",
    "componente",
    "mantenimiento",
    "reparación",
    "frenos",
    "motor",
    "battery",
    "engine",
]


def should_use_tools(query: str):

    query = query.lower()

    return any(
        keyword in query
        for keyword in FUNCTION_KEYWORDS
    )