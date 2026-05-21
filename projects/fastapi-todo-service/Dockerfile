# Multi-stage build for optimal image size
FROM python:3.14-slim AS builder

RUN pip install poetry
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1

WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --without dev

FROM python:3.14-slim AS runtime
WORKDIR /app
COPY .version ./
COPY README.md ./
COPY docs ./docs

# Ensure python searches the src directory for the fastapi_todo_service package
ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app/.venv /app/.venv
COPY src /app/src

EXPOSE 8000

# Updated to use the proper module path instead of the file path
CMD ["uvicorn", "fastapi_todo_service.main:app", "--host", "0.0.0.0", "--port", "8000"]