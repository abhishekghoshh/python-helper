FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HUB_DISABLE_TELEMETRY=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only torch first (avoids pulling multi-GB CUDA wheels)
RUN pip install --no-cache-dir --retries 5 torch==2.5.1 \
    --index-url https://download.pytorch.org/whl/cpu

# Install project dependencies including RAG extras
COPY pyproject.toml README.md ./
COPY app/ ./app/
RUN pip install --no-cache-dir ".[rag]"

# Pre-download the embedding model so containers start without a slow
# first-request download (and don't depend on network at runtime).
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
