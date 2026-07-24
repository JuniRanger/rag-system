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
                        "Fecha y hora confirmadas, formato exacto YYYY-MM-DD HH:MM. "
                        "Si el usuario dio fecha sin hora, usa 10:00. "
                        "Ejemplo: 2026-07-20 15:00"
                    ),
                },
                "vehiculo": {
                    "type": "string",
                    "description": (
                        "Marca, modelo y año dichos por el usuario. "
                        "Ejemplo: Mazda 3 2018"
                    ),
                },
                "producto": {
                    "type": "string",
                    "description": (
                        "Servicio o componente confirmado. "
                        "Ejemplo: Balatas delanteras"
                    ),
                },
            },
            "required": ["fecha", "vehiculo", "producto"],
        },
    },
}
