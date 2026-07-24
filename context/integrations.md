# Integraciones Externas

| Sistema | Uso | Módulos |
| ------- | --- | ------- |
| **Ollama** | Generación, tool calling, summary, warmup | `app/llm/providers/ollama.py`, `app/llm/ollama_client.py` |
| **Qdrant Cloud** | Almacén vectorial (upsert + search) | `app/vectorstore/providers/qdrant.py` |
| **Hugging Face / Sentence Transformers** | Embeddings + CrossEncoder reranker | `app/embeddings/`, `app/retrieval/reranker.py` |
| **Supabase** | Ingesta sync/webhook + tools SELECT | `app/core/supabase.py`, `app/ingestion/`, `app/tools/.../read_tools.py` |
| **API de citas** | Agendar servicio | `app/tools/implementations/citas.py` |
| **Azure** (previsto) | LLM / embeddings / Cosmos | Stubs `NotImplementedError` |

## Notas por integración

### Ollama

- URL efectiva: override `OLLAMA_BASE_URL` o auto-detect local/docker (`app/core/config.py`).
- Function calling vía `chat_with_tools_async`.
- Fallback de modelo si el primario no existe (`OLLAMA_MODEL_FALLBACK`).

### Qdrant Cloud

- `QDRANT_URL` y `QDRANT_API_KEY` obligatorios (sin defaults en Settings).
- Colección configurable (`QDRANT_COLLECTION_NAME`, default `documents`).

### Supabase

- Configurado si existen `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` + `SUPABASE_TABLE`.
- Sync: full / incremental con cursor.
- Webhook: solo eventos `INSERT` de la tabla configurada.
- Auth: headers `X-Sync-Secret` / `X-Webhook-Secret`.

### API de citas

- Base: `CITAS_API_BASE_URL` (default en config apunta a un servicio Render).
- Path: `/citas/agendar`.
- Timeout HTTP: 30s (`httpx`).

### Azure (no implementado)

- `PROVIDER_TYPE=AZURE` selecciona providers que lanzan `NotImplementedError` al instanciarse:
  - `AzureGPTLLMProvider`
  - `AzureOpenAIEmbeddingProvider`
  - `AzureCosmosVectorStoreProvider`

## Lo que no existe en el repo

- Clientes MCP
- LangChain / frameworks de agentes externos
- Orquestadores distintos del tool loop propio (`app/rag/tool_loop.py`)

## Ver también

- [tools.md](./tools.md)
- [environment.md](./environment.md)
- [architecture.md](./architecture.md)
