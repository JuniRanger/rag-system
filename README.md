# RAG System

Local **Retrieval-Augmented Generation** API: Ingests documents (PDF/TXT/MD), indexes them into **Qdrant** using **Sentence Transformers** embeddings, and answers questions with **Ollama** relying strictly on the retrieved context.

---

## Architecture

```

PDF/TXT  →  Ingestion  →  Chunks  →  Embeddings  →  Qdrant Cloud
↑
Question →  Embedding  →  Search  →  Rerank (LLM)   →  Generation (Ollama)

```

| Component  | Technology                                     | Role                        |
| ---------- | ---------------------------------------------- | --------------------------- |
| API        | FastAPI + Uvicorn                              | HTTP Endpoints              |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (384d) | Text → Vectors              |
| Vector DB  | Qdrant Cloud (HNSW, cosine)                    | Storage and Semantic Search |
| LLM        | Ollama (`llama3.2:1b` by default)              | Rerank + Final Answer       |

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
- A [Qdrant Cloud](https://cloud.qdrant.io/) cluster (URL + API key)
- [Docker](https://docs.docker.com/) and Docker Compose (optional, for packaging the API)
- [Ollama](https://ollama.ai/) running on the host machine (Local GPU/CPU; does not run inside the API container)

```bash
ollama pull llama3.2:1b
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
OLLAMA_MODEL=llama3:8b
OLLAMA_KEEP_ALIVE=24h

# Qdrant Cloud (required) — from the Qdrant Cloud console
QDRANT_URL=https://YOUR-CLUSTER-ID.REGION.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-cloud-api-key
QDRANT_COLLECTION_NAME=documents

EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
EMBEDDING_DIMENSION=384

CHUNK_SIZE=500
CHUNK_OVERLAP=50
TOP_K=10
DEBUG=False

```

### Qdrant Cloud setup

1. Create a cluster in [Qdrant Cloud](https://cloud.qdrant.io/).
2. Copy the cluster **URL** and **API Key** from the console.
3. Set them in `.env` as `QDRANT_URL` and `QDRANT_API_KEY` (no defaults in the app).
4. Keep `QDRANT_COLLECTION_NAME=documents` unless you intentionally use another collection name.

When running the API container, set `OLLAMA_BASE_URL=http://host.docker.internal:11434` so the container can reach Ollama on the host (see Docker section below). Qdrant is always remote (Cloud); do not point it at Docker networking.

## Local Deployment (Without API Docker container)

### 1. Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

```

### 2. Configure Qdrant Cloud

Ensure `.env` has a valid `QDRANT_URL` and `QDRANT_API_KEY` (see above). No local Qdrant container is required.

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

## Docker Deployment (API only)

The API is built using `docker/app.dockerfile`. **Ollama runs natively on the host** (via `host.docker.internal`). **Qdrant runs in Qdrant Cloud** (credentials from `.env`).

```bash
# Run from the project root directory
docker compose up -d --build

```

Services:

| Service | Port | Description         |
| ------- | ---- | ------------------- |
| `app`   | 8000 | FastAPI Application |

Compose notes:

- `QDRANT_URL` and `QDRANT_API_KEY` come from `.env` (`env_file`)
- `OLLAMA_BASE_URL=http://host.docker.internal:11434` for host Ollama

Mounted Volumes: `data/`, Hugging Face cache. `.env` is loaded via `env_file`.

Standalone API Image Build:

```bash
docker build -f docker/app.dockerfile -t rag-system-api .
docker run --rm -p 8000:8000 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  --env-file .env \
  -v "$(pwd)/data:/app/data" \
  rag-system-api

```

## Endpoints

| Method | Route                     | Description                                                   |
| ------ | ------------------------- | ------------------------------------------------------------- |
| GET    | `/api/v1/health`          | Ollama + Qdrant connection status                             |
| POST   | `/api/v1/ingest`          | Indexes `source_path` (file or folder)                        |
| POST   | `/api/v1/query`           | Executes the RAG query pipeline                               |
| POST   | `/api/v1/evaluate`        | Runs a system performance benchmark (`dataset_path` optional) |
| GET    | `/api/v1/collection/info` | Fetches Qdrant collection statistics and details              |

## Under the Hood (How it was built)

1. **Ingestion** (`app/ingestion/`): Extracts text from source PDFs, cleans it, splits it into overlapping fragments, and caches a copy in `data/chunks/chunks.json`.
2. **Embeddings** (`app/embeddings/`): Maps each text chunk to a normalized $384$-dimensional vector.
3. **Indexing** (`app/vectorstore/`): Upserts points into Qdrant alongside data payloads containing `text`, `filename`, `chunk_index`, and search `score`.
4. **Query Engine** (`app/rag/chain.py`):

- Performs a semantic search filtered by a 0.4 threshold setting (`TOP_K` candidates).
- Runs a batch reranking pipeline via the LLM to filter down to the top 3 chunks.
- Applies a highly restrictive system prompt (`app/core/prompts.py`) forcing the engine to reply _only_ using the matched context.

5. **Startup Handling** (`lifespan` in `main.py`): Pre-loads the embedding network, verifies Qdrant Cloud reachability, and warms up Ollama memory state (`num_predict: 1`).
6. **Evaluation Module** (`app/evaluation/`): Evaluates $N$ validation queries through the pipeline to compute core performance metrics: Precision, Recall, Faithfulness, and Relevancy, generating an export at `data/processed/evaluation_report.json`.

## Data Storage on Disk

| Path                                    | Description                                       |
| --------------------------------------- | ------------------------------------------------- |
| `data/raw/`                             | Raw source documents                              |
| `data/chunks/chunks.json`               | Generated text chunks after ingestion             |
| `data/processed/evaluation_report.json` | JSON output file containing evaluation benchmarks |

## Tests

```bash
pytest tests/

```

## License

Academic Project / Deliverable
