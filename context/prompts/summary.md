# Prompt de Resumen Conversacional

Fuente: `app/core/prompts.py`  
Uso: `ConversationSummarizer` en `app/rag/memory.py`.

## CONVERSATION_SUMMARY_PROMPT

* **Archivo:** `app/core/prompts.py`
* **Propósito:** Actualizar un resumen **pasivo y factual** de la conversación (no estado activo de vehículo).
* **Cuándo se utiliza:** Tras generar la respuesta, si `should_refresh_summary(request)` — cada **3** mensajes de usuario (`SUMMARY_REFRESH_INTERVAL = 3`).
* **Entradas:** `{previous_summary}`, `{recent_messages}`, `{user_message}`, `{assistant_answer}`.
* **Salidas:** Solo el texto del resumen (3–4 oraciones).
* **Dependencias:** `ConversationSummarizer` + LLM con `temperature=0.3`, `num_predict=256`.
* **Flujo:** Pipeline → answer → summarize → campo `summary` en `RAGResponse`.
* **Observaciones:**
  * El summary **no** se inyecta en los prompts de generación de respuesta del turno actual.
  * El cliente debe reenviarlo en el siguiente request.
  * La **working memory** sí va a los prompts RAG/tools (memoria dual).
  * Instrucciones del prompt prohíben inferir rol del usuario y tratar el resumen como estado activo permanente.

## Relación con otras memorias

| Concepto | Persistencia | ¿Entra al prompt de respuesta? |
| -------- | ------------ | ------------------------------ |
| `working_memory` | Request/response | Sí (RAG y agent) |
| `summary` | Request/response | No (solo en este prompt de update) |
| `recent_messages` | Request | Sí, solo si el plan incluye historial |

## Ver también

- [../flows.md](../flows.md)
- [conversation.md](./conversation.md) — `MEMORY_REQUEST` usa historial, no summary
- [README.md](./README.md)
