# Imagen de la API RAG (FastAPI + embeddings locales)
FROM python:3.11-slim

WORKDIR /app

# Evita archivos innecesarios de Python + optimiza pip
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface

# Dependencias mínimas del sistema (sin overkill)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.3.1
RUN pip install --no-cache-dir -r requirements.txt

# Código de la aplicación
COPY app/ ./app/
COPY scripts/ ./scripts/

# Directorios de trabajo
RUN mkdir -p data/raw data/chunks data/processed logs \
    && mkdir -p /app/.cache/huggingface

# Exponer API
EXPOSE 8000

# Healthcheck básico
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Startup
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]