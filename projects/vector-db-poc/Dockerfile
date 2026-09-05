FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only torch first (avoids pulling multi-GB CUDA wheels)
RUN pip install --no-cache-dir --retries 5 torch==2.5.1 \
    --index-url https://download.pytorch.org/whl/cpu

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.5

# Copy dependency manifests
COPY pyproject.toml poetry.lock ./

RUN poetry install --only=main --no-interaction --no-cache

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
