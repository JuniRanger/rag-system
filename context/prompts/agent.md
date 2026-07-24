# Prompts del Agente (Tool Calling)

Fuente: `app/llm/prompts/`  
Uso: `app/rag/tool_loop.py` → `_build_tool_prompt` cuando `plan.use_tools` y tools activas.

Ver catálogo de tools: [../tools.md](../tools.md).  
Ver diagrama del loop: [../flows.md](../flows.md).

## TOOL_AUGMENTED_RAG_PROMPT

* **Archivo:** `app/llm/prompts/tool_augmented_rag.py`
* **Propósito:** Prompt principal del agente con tools: diagnóstico +/o agendamiento (`crearCitaAPI`), con rol, modo de tools y perfil de usuario.
* **Cuándo se utiliza:** `plan.use_tools == True` **y** `ENABLE_RAG_TOOLS` **y** hay tools registradas.
* **Entradas:**
  * `{today_date}` — `date.today().isoformat()`
  * `{user_role}` — `admin` | `client`
  * `{role_rules}` — `ROLE_RULES_ADMIN` o `ROLE_RULES_CLIENT`
  * `{user_profile}` — texto de `RAGUser.to_cita_prompt_text()`
  * `{tool_mode}` — `all` | `scheduling` | `none`
  * `{tool_mode_rules}` — fragmento correspondiente
  * `{working_memory}`, `{conversation_context}`, `{context}`, `{question}`
* **Salidas:** Prosa al usuario y/o **tool_calls** nativos (no JSON en texto). Tras tools, respuesta final en lenguaje natural.
* **Dependencias:** Tool registry, `tool_executor`, inyección servidor de `usuario` en `crearCitaAPI`, filtrado de schemas por rol/modo.
* **Observaciones:** En modo `scheduling`, el contexto documental se reemplaza por un placeholder fijo (“sin contexto documental — modo agendamiento”).

## TOOL_MODE_RULES_SCHEDULING / ALL / NONE

* **Archivo:** `app/llm/prompts/tool_mode_rules_scheduling.py`, `tool_mode_rules_all.py`, `tool_mode_rules_none.py`
* **Propósito:** Fragmentos inyectados en `{tool_mode_rules}` según el modo del plan.
* **Cuándo:** Siempre que se construye `TOOL_AUGMENTED_RAG_PROMPT`.
* **Entradas:** Ninguna (texto estático).
* **Dependencias:** `GenerationPlan.tool_mode` desde `plan_request`.
* **Flujo:** `_tool_mode_rules(tool_mode)` en `tool_loop.py`.
* **Contenido resumido:**
  * `scheduling`: recopilar vehículo → servicio → fecha; solo `crearCitaAPI`; ignorar docs técnicos.
  * `all`: tools Supabase + citas.
  * `none`: sin tools (texto residual; en práctica el plan no activa tools en ese modo).

## ROLE_RULES_ADMIN / ROLE_RULES_CLIENT

* **Archivo:** `app/llm/prompts/role_rules_admin.py`, `role_rules_client.py`
* **Propósito:** Restricciones por rol en el prompt de tools.
* **Cuándo:** Prompt aumentado con tools.
* **Dependencias:** `request.user.perfil.role` (default `client`).
* **Flujo:** Además del prompt, el código **bloquea** `crearCitaAPI` para admin en `_tools_for_mode` y en ejecución.
* **Observaciones:** Defensa en profundidad: prompt + filtro de schemas + check en `_execute_tool_rounds`.

## TOOL_FINAL_USER_NUDGE

* **Archivo:** `app/llm/prompts/tool_final_user_nudge.py`
* **Propósito:** Tras rondas de tools sin `content` final, se añade un mensaje `role=user` pidiendo respuesta en prosa y prohibiendo nuevas tool calls.
* **Cuándo:** `needs_final_stream` y aún no hay `answer` en `_execute_tool_rounds`.
* **Entradas:** N/A (string constante).
* **Dependencias:** Historial de mensajes del tool loop (assistant tool_calls + role tool).
* **Flujo:** Tool rounds → append nudge → `generate_response_async` o stream.

## Descripciones de tools (schemas)

* **Archivos:** `app/tools/schemas/supabase.py`, `app/tools/schemas/citas.py`
* **Propósito:** Instrucciones al modelo (`description` + parámetros) para function calling Ollama.
* **Cuándo:** Se envían como `tools=[...]` en `chat_with_tools_async` cuando el modo lo permite.
* **Observaciones:** Para `crearCitaAPI` el schema solo expone `fecha`, `vehiculo`, `producto`; el servidor inyecta `usuario` desde el request.

## Respuesta fija asociada

`ADMIN_SCHEDULING_DENIED` en `app/rag/tool_loop.py` — cuando un admin entra en modo scheduling y no hay tools de cita disponibles.

## Ver también

- [../tools.md](../tools.md)
- [../intents.md](../intents.md)
- [rag.md](./rag.md)
