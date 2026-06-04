# # Imagen de la API RAG (FastAPI + embeddings locales)
# FROM python:3.11-slim

# WORKDIR /app

# ENV PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1 \
#     PIP_NO_CACHE_DIR=1 \
#     HF_HOME=/app/.cache/huggingface \
#     TRANSFORMERS_CACHE=/app/.cache/huggingface

# # Dependencias del sistema para wheels de ML
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     curl \
#     && rm -rf /var/lib/apt/lists/*

# COPY requirements.txt .
# RUN pip install --upgrade pip && pip install -r requirements.txt

# # Precarga del modelo de embeddings (arranque más rápido en runtime)
# RUN python -c "\
# from sentence_transformers import SentenceTransformer; \
# SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"

# COPY app/ ./app/
# COPY scripts/ ./scripts/

# RUN mkdir -p data/raw data/chunks data/processed logs

# EXPOSE 8000

# HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
#     CMD curl -f http://localhost:8000/api/v1/health || exit 1

# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
