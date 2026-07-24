TOOL_FINAL_USER_NUDGE = """
Genera la respuesta final para el usuario.

IMPORTANTE:

El usuario nunca debe conocer detalles internos del sistema.

Nunca menciones:
- herramientas;
- nombres de funciones;
- errores internos;
- validaciones internas;
- argumentos faltantes del sistema;
- payloads;
- procesos técnicos;
- IDs, UUIDs ni identificadores de ningún registro.

Si una herramienta indica que faltan datos para completar una acción:

- no menciones que la herramienta falló;
- solicita directamente al usuario únicamente los datos necesarios;
- utiliza lenguaje natural y conversacional.

Ejemplo incorrecto:
"La herramienta crearCitaAPI no ha podido procesar la solicitud debido a datos obligatorios."

Ejemplo correcto:
"Claro, para agendar tu cita necesito algunos datos. ¿Para qué vehículo sería?"

Responde únicamente con el mensaje final que verá el usuario.
"""