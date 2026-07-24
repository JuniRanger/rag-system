# Documentación técnica — RAG System

Índice de la documentación generada a partir del código fuente. **No inventa comportamiento no presente en el código.**

## Contenido

| Documento | Responsabilidad |
| --------- | --------------- |
| [architecture.md](./architecture.md) | Objetivo, capas, tecnologías, estructura de carpetas, diagrama de arquitectura |
| [flows.md](./flows.md) | Arranque, consulta, ingesta, evaluación y diagramas de flujo |
| [intents.md](./intents.md) | Router de intents, ramas, mapeo a RAG/tools/prompts |
| [prompts/](./prompts/README.md) | Inventario y documentación de cada prompt |
| [tools.md](./tools.md) | Function calling, registry, tools Supabase y citas |
| [integrations.md](./integrations.md) | Ollama, Qdrant, Supabase, API de citas, Azure (stubs) |
| [environment.md](./environment.md) | Variables de entorno y configuraciones importantes |
| [risks.md](./risks.md) | Riesgos, mejoras detectadas y resumen final |

## Lectura recomendada (onboarding)

1. [architecture.md](./architecture.md)
2. [flows.md](./flows.md) + [intents.md](./intents.md)
3. [prompts/README.md](./prompts/README.md)
4. [tools.md](./tools.md)
5. Código: `app/core/prompts.py` → `app/rag/context_plan.py` → `app/llm/generator.py` → `app/rag/tool_loop.py`
