# Riesgos, Mejoras y Resumen

## Riesgos

1. **`OUT_OF_SCOPE_PROMPT` no se usa** en el flujo actual (rechazo estático vía sentinel); posible divergencia documentación/código.
2. **Heurística de intent por regex** puede fallar en mensajes ambiguos, idiomas no cubiertos, o falsos positivos/negativos de marcas/términos.
3. **`ENABLE_RAG_TOOLS=true`** depende de la calidad del function calling del modelo Ollama; existe sanitización `_strip_tool_json_leak` porque el modelo puede filtrar JSON.
4. **Service role de Supabase** en el backend: potente; tools actuales son solo lectura, pero la clave debe protegerse.
5. **Provider Azure** seleccionable en config pero **rompe al arrancar/usar** (`NotImplementedError`).
6. **Umbral 0.4 hardcodeado** — no configurable por env; puede devolver vacío o ruido según colección.
7. **Admin bloqueado solo para citas**; tools de lectura Supabase siguen disponibles en modo `all` para admin (si aplica).
8. **Datos de usuario incompletos** → `crearCitaAPI` falla en runtime aunque el LLM llame la tool.
9. **README** describe parcialmente el sistema antiguo (p. ej. rerank “vía LLM”); el código usa CrossEncoder local y un flujo conversacional + tools más rico.

## Mejoras detectadas

1. Eliminar o cablear `OUT_OF_SCOPE_PROMPT` para evitar código muerto.
2. Extraer umbral de retrieval y `MAX_TOOL_ROUNDS` a settings.
3. Unificar estimación de tokens: hoy `_build_prompt` RAG puede contarse aunque la generación real use `TOOL_AUGMENTED_*`.
4. Completar o quitar stubs Azure / archivos vacíos `write_tools` / `admin_tools`.
5. Actualizar README para reflejar intents, working memory, tools y streaming.
6. Evaluar clasificador de intent con LLM si las regex resultan insuficientes.
7. Documentar contrato exacto del frontend (`user`, `working_memory`, `summary`, `recent_messages`) — el schema Pydantic en `app/rag/schemas.py` ya es la fuente de verdad.

## Resumen final

Este repositorio es un **RAG conversacional de mecánica automotriz** con:

- **Un solo archivo central de prompts** (`app/core/prompts.py`).
- Un **planificador heurístico** (`intent` + `context_plan`) que enruta a prompts ligeros, RAG estricto, o un **agente con function calling**.
- **Memoria dual:** `working_memory` (activa, en prompts) y `summary` (pasiva, prompt aparte cada 3 turnos).
- **Tools** opcionales de consulta Supabase + agendamiento de citas, gobernadas por `ENABLE_RAG_TOOLS`, rol y `tool_mode`.
- Stack local **Ollama + Sentence Transformers + Qdrant Cloud**, con Supabase y API de citas como integraciones externas.

Onboarding sugerido: [README.md](./README.md).

## Inventario de verificación de prompts

| Prompt / fragmento | Documento |
| ------------------ | --------- |
| `RAG_SYSTEM_PROMPT` | [prompts/rag.md](./prompts/rag.md) |
| `SUPABASE_RAG_PROMPT` | [prompts/rag.md](./prompts/rag.md) |
| `CONVERSATION_PROMPT` | [prompts/conversation.md](./prompts/conversation.md) |
| `MEMORY_REQUEST_PROMPT` | [prompts/conversation.md](./prompts/conversation.md) |
| `OUT_OF_SCOPE_PROMPT` | [prompts/conversation.md](./prompts/conversation.md) |
| `TOOL_AUGMENTED_RAG_PROMPT` + fragments | [prompts/agent.md](./prompts/agent.md) |
| `CONVERSATION_SUMMARY_PROMPT` | [prompts/summary.md](./prompts/summary.md) |
| Schemas tools | [tools.md](./tools.md) |
| Flujos query / stream / ingest | [flows.md](./flows.md) |
| MCP | No aplica (no existe en el repo) |
