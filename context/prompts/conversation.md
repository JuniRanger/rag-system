# Prompts Conversacionales y Fuera de Dominio

Fuente: `app/llm/prompts/`  
Selección: `ResponseGenerator._build_prompt` según `QueryIntent`.

## CONVERSATION_PROMPT

* **Archivo:** `app/llm/prompts/conversation.py`
* **Propósito:** Respuestas cortas y naturales sin diagnóstico ni documentos.
* **Cuándo se utiliza:** `QueryIntent.CONVERSATION`.
* **Entradas:** `{question}`.
* **Salidas:** 1–pocas frases conversacionales.
* **Dependencias:** Ninguna retrieval; `run_rag=False`, `use_tools=False`.
* **Flujo:** Intent conversation → skip RAG → prompt → LLM.
* **Observaciones:** Si la pregunta es ambigua (“¿qué opinas?”) sin contexto activo, el intent router ya puede clasificarla como conversation.

## MEMORY_REQUEST_PROMPT

* **Archivo:** `app/llm/prompts/memory_request.py`
* **Propósito:** Responder preguntas sobre la conversación previa usando solo `conversation_context`.
* **Cuándo se utiliza:** `QueryIntent.MEMORY_REQUEST`.
* **Entradas:** `{conversation_context}`, `{question}`.
* **Salidas:** Respuesta factual sobre lo hablado; sin diagnóstico ni RAG.
* **Dependencias:** `format_conversation_context(plan.summary, plan.recent_messages)` en `ResponseGenerator._build_prompt`.
* **Flujo:** Intent memory → skip RAG → prompt con `conversation_context` → LLM.
* **Observaciones:** No usa `conversation_history`, working_memory ni chunks documentales. El contexto conversacional puede incluir resumen + mensajes recientes cuando `include_conversation_history=True`.

## OUT_OF_SCOPE_PROMPT

* **Archivo:** `app/llm/prompts/out_of_scope.py`
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
