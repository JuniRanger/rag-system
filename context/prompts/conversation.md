# Prompts Conversacionales y Fuera de Dominio

Fuente: `app/core/prompts.py`  
Selección: `ResponseGenerator._build_prompt` según `QueryIntent`.

## CONVERSATION_PROMPT

* **Archivo:** `app/core/prompts.py`
* **Propósito:** Respuestas cortas y naturales sin diagnóstico ni documentos.
* **Cuándo se utiliza:** `QueryIntent.CONVERSATION`.
* **Entradas:** `{question}`.
* **Salidas:** 1–pocas frases conversacionales.
* **Dependencias:** Ninguna retrieval; `run_rag=False`, `use_tools=False`.
* **Flujo:** Intent conversation → skip RAG → prompt → LLM.
* **Observaciones:** Si la pregunta es ambigua (“¿qué opinas?”) sin contexto activo, el intent router ya puede clasificarla como conversation.

## MEMORY_REQUEST_PROMPT

* **Archivo:** `app/core/prompts.py`
* **Propósito:** Responder preguntas sobre lo hablado recientemente usando solo el historial.
* **Cuándo se utiliza:** `QueryIntent.MEMORY_REQUEST`.
* **Entradas:** `{conversation_history}`, `{question}`.
* **Salidas:** Respuesta factual sobre mensajes previos; sin diagnóstico.
* **Dependencias:** `request.recent_messages` formateados en el plan (`include_history=True`).
* **Flujo:** Intent memory → skip RAG → prompt con historial → LLM.
* **Observaciones:** El **summary** pasivo **no** se inyecta en este prompt (solo `recent_messages`). Tests lo verifican (`test_memory_request_uses_history_not_summary_in_prompt`).

## OUT_OF_SCOPE_PROMPT

* **Archivo:** `app/core/prompts.py`
* **Propósito:** Rechazar amablemente temas no automotrices vía LLM.
* **Cuándo se utiliza:** En `_build_prompt` si `intent == OUT_OF_SCOPE`.
* **Entradas:** `{question}`.
* **Salidas:** Rechazo amable, sin conocimiento general.
* **Dependencias:** —
* **Flujo / Observaciones importantes:** En la práctica, cuando el intent es `OUT_OF_SCOPE`, `plan_request` sustituye la pregunta por el sentinel **`REJECT_OUT_OF_SCOPE_REQUEST`**. `ResponseGenerator.generate` / `stream_generate` interceptan ese sentinel y devuelven **`REJECTION_ANSWER` sin llamar al LLM**. Por tanto, **`OUT_OF_SCOPE_PROMPT` queda efectivamente sin uso en el camino feliz actual** (código muerto / legado), salvo que se cambie esa interceptación.

## Respuesta fija asociada

`REJECTION_ANSWER` en `app/llm/generator.py` — texto estático de rechazo especializado en mecánica. También aplica cuando hay **palabras prohibidas** (inyección / SQL / system prompt, etc.).

## Ver también

- [../intents.md](../intents.md)
- [summary.md](./summary.md)
- [rag.md](./rag.md)
