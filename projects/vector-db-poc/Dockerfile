FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry with the export plugin (for generating pip requirements)
RUN pip install --no-cache-dir poetry==2.4.3 poetry-plugin-export

# Install CPU-only torch first (avoids pulling multi-GB CUDA wheels)
RUN pip install --no-cache-dir --retries 5 torch==2.5.1 \
    --index-url https://download.pytorch.org/whl/cpu

# Copy dependency manifests
COPY pyproject.toml poetry.lock ./

# Export Python dependencies from the Poetry lock file, then install with pip.
# torch and nvidia-*/cuda-*/triton CUDA packages are excluded because
# CPU-only torch was installed in the layer above (avoids multi-GB downloads).
RUN poetry export --only=main --without-hashes -o /tmp/requirements.txt \
    && grep -viE '^(torch|nvidia-|cuda-|triton)' /tmp/requirements.txt > /tmp/requirements-filtered.txt \
    && pip install --no-cache-dir --retries 5 -r /tmp/requirements-filtered.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
