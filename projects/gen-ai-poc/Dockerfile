FROM python:3.11-slim AS base

LABEL maintainer="GenAI POC"

# OS-level deps needed by numpy and sentence-transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry + the export plugin (for exporting lock-file deps to pip format)
ENV POETRY_VERSION=2.4.1
ENV POETRY_HOME=/opt/poetry
ENV PATH="$POETRY_HOME/bin:$PATH"
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION" && \
    poetry self add --no-interaction poetry-plugin-export

WORKDIR /app

# Copy dependency files first (for layer caching)
COPY pyproject.toml poetry.lock ./

# Export main deps from Poetry lock file to requirements.txt, then install via pip.
# CPU-only torch is installed separately from PyTorch's CPU index to avoid
# downloading large CUDA packages (e.g. nvidia-nccl-cu13, nvidia-cublas-cu13)
# that are too large to download reliably in a Docker build.
RUN poetry export --only=main --without-hashes -o /tmp/requirements.txt && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch && \
    grep -v "nvidia-" /tmp/requirements.txt | grep -v "^torch==" > /tmp/requirements-filtered.txt && \
    pip install --no-cache-dir -r /tmp/requirements-filtered.txt && \
    rm -f /tmp/requirements.txt /tmp/requirements-filtered.txt

# Copy application code
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
