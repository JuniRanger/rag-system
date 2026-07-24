# Prompts RAG (sin tools)

Fuente: `app/llm/prompts/`  
Selección: `ResponseGenerator._build_prompt` cuando el intent cae en generación documental **y** no se usa el tool loop.

Condición de template:

- `supabase_configured() == False` → `RAG_SYSTEM_PROMPT`
- `supabase_configured() == True` → `SUPABASE_RAG_PROMPT`

## RAG_SYSTEM_PROMPT

* **Archivo:** `app/llm/prompts/rag_system.py`
* **Propósito:** Prompt monolítico de asistente de mecánica. Obliga a responder solo con historial + contexto recuperado; clasifica consultas A/B/C (conversacional / mecánica / fuera de dominio); prohíbe inventar y filtrar IDs/metadata.
* **Cuándo se utiliza:** Intent `AUTOMOTIVE` (o caída al template RAG) **sin** tool calling activo, y **Supabase no configurado**.
* **Entradas (placeholders):**
  * `{working_memory}` — memoria activa de diagnóstico
  * `{conversation_context}` — resumen + mensajes recientes formateados (si el plan incluye historial)
  * `{context}` — fragmentos recuperados formateados
  * `{question}` — pregunta actual
* **Salidas esperadas:** Texto de respuesta al usuario en el idioma del usuario, fiel al contexto.
* **Dependencias:** `WorkingMemory.to_prompt_text()`, `_build_context()`, `format_conversation_context(plan.summary, plan.recent_messages)`.
* **Flujo:** `plan_request` → RAG retrieve → `_build_prompt` → `llm.generate_response_async` / stream.
* **Observaciones:** Es el prompt más restrictivo y largo. Con tools activas **no** es el prompt efectivo de generación (sí puede usarse para estimar `tokens_input` antes de entrar al tool loop).

## SUPABASE_RAG_PROMPT

* **Archivo:** `app/llm/prompts/supabase_rag.py`
* **Propósito:** Variante RAG más corta cuando la fuente documental es Supabase (sin tool calling). Misma estructura de entradas que `RAG_SYSTEM_PROMPT`.
* **Cuándo se utiliza:** Misma rama que arriba, pero `supabase_configured() == True` y **sin** tools en la generación.
* **Entradas:** `{working_memory}`, `{conversation_context}`, `{context}`, `{question}`.
* **Salidas:** Respuesta de diagnóstico basada en contexto.
* **Dependencias:** `app/core/supabase.supabase_configured()`.
* **Flujo:** Idéntico a `RAG_SYSTEM_PROMPT` con otro template.
* **Observaciones:** Comentario en código: preserva IDs/datos técnicos que el flujo con tools incluía antes; es menos verboso en reglas de confidencialidad que `RAG_SYSTEM_PROMPT`.

## Formato del contexto inyectado

`ResponseGenerator._build_context` arma cada fragmento como:

```text
[Fragmento N | ID registro: … | Fuente: …]
texto del chunk
```

Separados por `---`. Si no hay chunks, usa `fallback_context` (`EMPTY_VECTOR_CONTEXT` o `NO_CONTEXT_ANSWER`).

## Ver también

- [../intents.md](../intents.md) — cuándo corre RAG
- [agent.md](./agent.md) — alternativa con tools
- [../flows.md](../flows.md)
