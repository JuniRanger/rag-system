from app.llm.prompts.base import BASE_SYSTEM_PROMPT

CONVERSATION_SUMMARY_PROMPT = f"""
{BASE_SYSTEM_PROMPT}

================================================================================
MODO: RESUMEN DE CONVERSACIÓN
================================================================================

Tu tarea es actualizar un resumen pasivo de la conversación.

Este resumen será utilizado únicamente como referencia histórica.
NO representa memoria activa del diagnóstico.

================================================================================
REGLAS DEL RESUMEN
================================================================================

1. Registra únicamente información mencionada explícitamente.

2. No inventes:
- vehículos;
- problemas;
- soluciones;
- diagnósticos;
- intenciones del usuario;
- rol del usuario.

3. No conviertas información temporal en una afirmación permanente.

Correcto:
"Se habló sobre una falla de transmisión en un Hyundai Santa Fe 2016."

Incorrecto:
"El usuario está reparando un Hyundai Santa Fe 2016."

4. No uses el resumen para mantener un diagnóstico activo.
La memoria activa del diagnóstico se maneja por separado mediante working_memory.

5. Si hubo múltiples vehículos o temas:
- conserva únicamente la información relevante mencionada;
- no mezcles problemas entre vehículos.

6. Mantén el resumen breve:
- máximo 3-4 oraciones;
- lenguaje factual y pasivo.

7. Devuelve únicamente el texto del resumen.
No agregues etiquetas, explicaciones ni formato adicional.

================================================================================
RESUMEN ANTERIOR
================================================================================

{{previous_summary}}

================================================================================
MENSAJES RECIENTES
================================================================================

{{recent_messages}}

================================================================================
ÚLTIMO INTERCAMBIO
================================================================================

Usuario:
{{user_message}}

Asistente:
{{assistant_answer}}

================================================================================
RESUMEN ACTUALIZADO
================================================================================
"""