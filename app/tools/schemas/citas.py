# app/tools/schemas/citas.py
#
# Solo 3 argumentos para el LLM. El objeto `usuario` lo inyecta el servidor
# desde el body del request (nunca lo pide ni lo inventa el modelo).

SCHEMA_CREAR_CITA = {
    "type": "function",
    "function": {
        "name": "crearCitaAPI",
        "description": (
            "Agenda una cita de servicio. "
            "Úsala únicamente cuando el usuario ya confirmó fecha, vehículo y producto/servicio. "
            "Si falta alguno de esos tres datos, NO llames esta herramienta: pregunta en texto. "
            "No inventes valores. El sistema adjunta automáticamente los datos del cliente."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "fecha": {
                    "type": "string",
                    "description": (
                        "Fecha y hora exactas confirmadas por el usuario, "
                        "formato YYYY-MM-DD HH:MM. "
                        "Si falta la fecha o la hora, NO llames la herramienta: "
                        "pregunta el dato faltante. "
                        "Nunca inventes ni completes con valores por defecto "
                        "(ni 10:00 ni ninguna fecha de ejemplo)."
                    ),
                },
                "vehiculo": {
                    "type": "string",
                    "description": (
                        "Marca, modelo y año dichos por el usuario. "
                        "Si falta, pregunta; no inventes."
                    ),
                },
                "producto": {
                    "type": "string",
                    "description": (
                        "Servicio o componente confirmado por el usuario. "
                        "Si falta, pregunta; no inventes."
                    ),
                },
            },
            "required": ["fecha", "vehiculo", "producto"],
        },
    },
}
