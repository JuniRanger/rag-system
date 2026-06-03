# RAG System

Local **Retrieval-Augmented Generation** API: Ingests documents (PDF/TXT/MD), indexes them into **Qdrant** using **Sentence Transformers** embeddings, and answers questions with **Ollama** relying strictly on the retrieved context.


---

## Architecture


```

PDF/TXT  →  Ingestion  →  Chunks  →  Embeddings  →  Qdrant
↑
Question →  Embedding  →  Search  →  Rerank (LLM)   →  Generation (Ollama)

```

| Component | Technology | Role |
|-----------|------------|------|
| API | FastAPI + Uvicorn | HTTP Endpoints |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (384d) | Text → Vectors |
| Vector DB | Qdrant (HNSW, cosine) | Storage and Semantic Search |
| LLM | Ollama (`qwen2.5:3b` by default) | Rerank + Final Answer |

### Project Structure


```

app/
├── main.py              # FastAPI, lifespan (models pre-loading)
├── api/                 # routes.py, schemas.py
├── core/                # config, prompts, logger
├── ingestion/           # loader → cleaner → chunker → pipeline
├── embeddings/          # SentenceTransformer
├── vectorstore/         # Qdrant client + indexer
├── retrieval/           # search + reranker
├── llm/                 # Ollama client + generator
├── rag/                 # chain + pipeline
└── evaluation/          # metrics and benchmark

```

## Requirements

- Python 3.11+
- [Docker](https://docs.docker.com/) and Docker Compose (optional, recommended for Qdrant + API)
- [Ollama](https://ollama.ai/) running on the host machine (Local GPU/CPU; does not run inside the API container)

```bash
ollama pull qwen2.5:3b
OLLAMA_KEEP_ALIVE=24h ollama serve

```

## Configuration

Copy the environment variables template:

```bash
cp .env.example .env

```

Typical configuration values in `.env`:

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

When running with Docker, set `QDRANT_HOST=qdrant` and `OLLAMA_BASE_URL=http://host.docker.internal:11434` (see Docker section below).

## Local Deployment (Without API Docker container)

### 1. Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

```

### 2. Qdrant

```bash
docker compose up -d qdrant

```

### 3. Start the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

```

Interactive API documentation will be available at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Typical Workflow

1. Place source PDFs into `data/raw/`.
2. **Ingest** — Processes and indexes data into Qdrant.
3. **Query** — Submit questions using natural language.
4. **Evaluate** (Optional) — Benchmarks performance using heuristic metrics.

```bash
# System Health Check
curl http://localhost:8000/api/v1/health

# Ingestion (Directory or single file)
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"source_path": "data/raw", "recreate_collection": true}'

# RAG Query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What does the document say about p95 latency?", "use_reranker": true}'

# Evaluation (Default dataset in-code, or provide a custom JSON path)
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"dataset_path": null}'

```

Equivalent CLI Scripts:

```bash
python scripts/ingest.py --source data/raw --recreate
python scripts/test_query.py   # If available in your environment

```

## Docker Deployment (Qdrant + API)

The API is built using `docker/app.dockerfile`. **Ollama runs natively on the host** (accessed via `host.docker.internal`).

```bash
# Run from the project root directory
docker compose up -d --build

```

Services:

| Service | Port | Description |
| --- | --- | --- |
| `qdrant` | 6333 | Vector Database |
| `app` | 8000 | FastAPI Application |

Compose Environment Variables for the `app` container:

* `QDRANT_HOST=qdrant`
* `OLLAMA_BASE_URL=http://host.docker.internal:11434`

Mounted Volumes: `data/`, `logs/`, `.env` (read-only).

Standalone API Image Build:

```bash
docker build -f docker/app.dockerfile -t rag-system-api .
docker run --rm -p 8000:8000 \
  -e QDRANT_HOST=host.docker.internal \
  -e OLLAMA_BASE_URL=[http://host.docker.internal:11434](http://host.docker.internal:11434) \
  --env-file .env \
  -v "$(pwd)/data:/app/data" \
  rag-system-api

```

## Endpoints

| Method | Route | Description |
| --- | --- | --- |
| GET | `/api/v1/health` | Ollama + Qdrant connection status |
| POST | `/api/v1/ingest` | Indexes `source_path` (file or folder) |
| POST | `/api/v1/query` | Executes the RAG query pipeline |
| POST | `/api/v1/evaluate` | Runs a system performance benchmark (`dataset_path` optional) |
| GET | `/api/v1/collection/info` | Fetches Qdrant collection statistics and details |

## Under the Hood (How it was built)

1. **Ingestion** (`app/ingestion/`): Extracts text from source PDFs, cleans it, splits it into overlapping fragments, and caches a copy in `data/chunks/chunks.json`.
2. **Embeddings** (`app/embeddings/`): Maps each text chunk to a normalized $384$-dimensional vector.
3. **Indexing** (`app/vectorstore/`): Upserts points into Qdrant alongside data payloads containing `text`, `filename`, `chunk_index`, and search `score`.
4. **Query Engine** (`app/rag/chain.py`):
* Performs a semantic search filtered by a 0.4 threshold setting (`TOP_K` candidates).
* Runs a batch reranking pipeline via the LLM to filter down to the top 3 chunks.
* Applies a highly restrictive system prompt (`app/core/prompts.py`) forcing the engine to reply *only* using the matched context.


5. **Startup Handling** (`lifespan` in `main.py`): Pre-loads the embedding network, verifies Qdrant node reachability, and warms up Ollama memory state (`num_predict: 1`).
6. **Evaluation Module** (`app/evaluation/`): Evaluates $N$ validation queries through the pipeline to compute core performance metrics: Precision, Recall, Faithfulness, and Relevancy, generating an export at `data/processed/evaluation_report.json`.

## Data Storage on Disk

| Path | Description |
| --- | --- |
| `data/raw/` | Raw source documents |
| `data/chunks/chunks.json` | Generated text chunks after ingestion |
| `data/processed/evaluation_report.json` | JSON output file containing evaluation benchmarks |
| `logs/rag_system.log` | Persistent application runtime logs |

## Tests

```bash
pytest tests/

```

## License

Academic Project / Deliverable
