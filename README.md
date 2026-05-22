# RAG System

API de **Retrieval-Augmented Generation** local: ingesta documentos (PDF/TXT/MD), los indexa en **Qdrant** con embeddings de **Sentence Transformers** y responde preguntas con **Ollama** usando solo el contexto recuperado.

## Arquitectura

```
PDF/TXT  →  Ingesta  →  Chunks  →  Embeddings  →  Qdrant
                                              ↑
Pregunta  →  Embedding  →  Búsqueda  →  Rerank (LLM)  →  Generación (Ollama)
```

| Componente | Tecnología | Rol |
|------------|------------|-----|
| API | FastAPI + Uvicorn | Endpoints HTTP |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (384d) | Texto → vectores |
| Vector DB | Qdrant (HNSW, cosine) | Almacén y búsqueda semántica |
| LLM | Ollama (`qwen2.5:3b` por defecto) | Rerank + respuesta final |

### Estructura del código

```
app/
├── main.py              # FastAPI, lifespan (precarga modelos)
├── api/                 # routes.py, schemas.py
├── core/                # config, prompts, logger
├── ingestion/           # loader → cleaner → chunker → pipeline
├── embeddings/          # SentenceTransformer
├── vectorstore/         # Qdrant client + indexer
├── retrieval/           # search + reranker
├── llm/                 # Ollama client + generator
├── rag/                 # chain + pipeline
└── evaluation/          # métricas y benchmark
```

## Requisitos

- Python 3.11+
- [Docker](https://docs.docker.com/) y Docker Compose (opcional, recomendado para Qdrant + API)
- [Ollama](https://ollama.ai/) en el host (GPU/CPU local; no va dentro del contenedor de la API)

```bash
ollama pull qwen2.5:3b
OLLAMA_KEEP_ALIVE=24h ollama serve
```

## Configuración

Copia las variables de entorno:

```bash
cp .env.example .env
```

Valores típicos en `.env`:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_KEEP_ALIVE=24h

QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=documents

EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSION=384

CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K=10
DEBUG=False
```

Con Docker, `QDRANT_HOST=qdrant` y `OLLAMA_BASE_URL=http://host.docker.internal:11434` (ver sección Docker).

## Uso local (sin Docker de la API)

### 1. Entorno virtual

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Qdrant

```bash
docker compose up -d qdrant
```

### 3. Arrancar la API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Documentación interactiva: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Flujo típico

1. Coloca PDFs en `data/raw/`.
2. **Ingesta** — indexa en Qdrant.
3. **Consulta** — pregunta en lenguaje natural.
4. **Evalúa** (opcional) — benchmark con métricas heurísticas.

```bash
# Salud del sistema
curl http://localhost:8000/api/v1/health

# Ingesta (carpeta o archivo)
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"source_path": "data/raw", "recreate_collection": true}'

# Consulta RAG
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "¿Qué dice el documento sobre latencia p95?", "use_reranker": true}'

# Evaluación (dataset por defecto en código; o JSON custom)
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"dataset_path": null}'
```

Scripts CLI equivalentes:

```bash
python scripts/ingest.py --source data/raw --recreate
python scripts/test_query.py   # si existe en tu entorno
```

## Docker (Qdrant + API)

La API se construye con `docker/app.dockerfile`. **Ollama sigue en el host** (acceso vía `host.docker.internal`).

```bash
# Desde la raíz del proyecto
docker compose up -d --build
```

Servicios:

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| `qdrant` | 6333 | Base vectorial |
| `app` | 8000 | API FastAPI |

Variables en Compose para el contenedor `app`:

- `QDRANT_HOST=qdrant`
- `OLLAMA_BASE_URL=http://host.docker.internal:11434`

Volúmenes montados: `data/`, `logs/`, `.env` (lectura).

Solo imagen de la API:

```bash
docker build -f docker/app.dockerfile -t rag-system-api .
docker run --rm -p 8000:8000 \
  -e QDRANT_HOST=host.docker.internal \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  --env-file .env \
  -v "$(pwd)/data:/app/data" \
  rag-system-api
```

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/health` | Estado Ollama + Qdrant |
| POST | `/api/v1/ingest` | Indexar `source_path` (archivo o carpeta) |
| POST | `/api/v1/query` | Pregunta RAG |
| POST | `/api/v1/evaluate` | Benchmark (`dataset_path` opcional) |
| GET | `/api/v1/collection/info` | Info de la colección Qdrant |

## Cómo fue construido

1. **Ingesta** (`app/ingestion/`): extrae texto del PDF, limpia, fragmenta con solapamiento y guarda copia en `data/chunks/chunks.json`.
2. **Embeddings** (`app/embeddings/`): cada chunk → vector 384D normalizado.
3. **Indexación** (`app/vectorstore/`): puntos en Qdrant con payload (`text`, `filename`, `chunk_index`, `score` en búsqueda).
4. **Consulta** (`app/rag/chain.py`):
   - Búsqueda semántica con umbral 0.4 (`TOP_K` candidatos).
   - Reranking batch con el LLM (top 3 chunks).
   - Prompt restrictivo (`app/core/prompts.py`) → respuesta solo del contexto.
5. **Arranque** (`lifespan` en `main.py`): precarga embedder, verifica Qdrant y calienta Ollama (`num_predict: 1`).
6. **Evaluación** (`app/evaluation/`): N preguntas → pipeline → métricas precision/recall/faithfulness/relevancy → `data/processed/evaluation_report.json`.

## Datos en disco

| Ruta | Contenido |
|------|-----------|
| `data/raw/` | Documentos fuente |
| `data/chunks/chunks.json` | Chunks tras ingesta |
| `data/processed/evaluation_report.json` | Reporte de evaluación |
| `logs/rag_system.log` | Logs de la aplicación |

## Tests

```bash
pytest tests/
```

## Licencia

Proyecto académico / entregable — ajusta según tu repositorio.
