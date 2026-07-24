# Variables de Entorno y Configuración

Fuente de verdad: `app/core/config.py` + `.env.example`.

## Variables

| Variable | Rol |
| -------- | --- |
| `OLLAMA_BASE_URL` | Override manual de URL Ollama |
| `OLLAMA_BASE_URL_LOCAL` / `OLLAMA_BASE_URL_DOCKER` | Auto-detect host vs contenedor |
| `OLLAMA_MODEL` / `OLLAMA_MODEL_FALLBACK` | Modelo primario y fallback |
| `OLLAMA_KEEP_ALIVE` | Persistencia del modelo en VRAM |
| `QDRANT_URL` / `QDRANT_API_KEY` | Obligatorios (sin default) |
| `QDRANT_COLLECTION_NAME` | Default `documents` |
| `EMBEDDING_MODEL_NAME` / `EMBEDDING_DIMENSION` / `EMBEDDING_BATCH_SIZE` | Embeddings |
| `RERANKER_MODEL_NAME` / `RERANKER_BATCH_SIZE` / `RERANKER_DEVICE` | CrossEncoder |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Fragmentación |
| `TOP_K` | Candidatos de retrieval |
| `DEBUG` | Flag app |
| `PROVIDER_TYPE` | `LOCAL` (prod actual) o `AZURE` (no implementado) |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` / `SUPABASE_TABLE` | Cliente + tools |
| `SUPABASE_ID_COLUMN` / `SUPABASE_CURSOR_COLUMN` | Sync incremental |
| `SUPABASE_TEXT_COLUMNS` | Columnas indexadas (CSV) |
| `SUPABASE_WEBHOOK_SECRET` / `SUPABASE_SYNC_SECRET` | Auth endpoints |
| `ENABLE_RAG_TOOLS` | Activa function calling en `/query` |
| `CITAS_API_BASE_URL` | Base URL API de citas |
| `RAW_DATA_PATH` / `PROCESSED_DATA_PATH` / `CHUNKS_DATA_PATH` | Rutas de datos |
| `APP_NAME` / `APP_VERSION` | Metadatos de la app (defaults en Settings) |

## Configuraciones importantes (código)

| Concepto | Valor / ubicación |
| -------- | ----------------- |
| Umbral score retrieval | `0.4` hardcodeado en `RAGChain.retrieve_context` |
| Max rondas de tools | `4` (`MAX_TOOL_ROUNDS` en `tool_loop.py`) |
| Refresh de summary | Cada 3 mensajes de usuario (`SUMMARY_REFRESH_INTERVAL`) |
| Reranker default | `use_reranker=True` en opciones de request |
| `max_chunks` default | 10 (`RAGQueryOptions`) |
| `top_k` default | 10 |
| Palabras prohibidas | SQL/hack/`system prompt`/etc. → `OUT_OF_SCOPE` (`context_plan.py`) |
| SSE eventos | `token`, `done` (`app/rag/sse.py`) |
| Chunk stream tools | 24 chars (`STREAM_CHUNK_SIZE`) |

## Resolución de URL Ollama

Prioridad en `settings.ollama_base_url`:

1. `OLLAMA_BASE_URL` (override) si no está vacío  
2. `OLLAMA_BASE_URL_DOCKER` si corre en contenedor  
3. `OLLAMA_BASE_URL_LOCAL` en host  

## Ver también

- [integrations.md](./integrations.md)
- [tools.md](./tools.md) — efecto de `ENABLE_RAG_TOOLS`
- [risks.md](./risks.md)
