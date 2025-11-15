# Use an official Python runtime as a base image
FROM python:3.13-slim-bookworm

# Set environment variables to prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

USER root
# install and configure poetry so dependencies installed directly into system (not venv)
RUN pip install poetry && poetry config virtualenvs.create false

RUN groupadd user
RUN adduser --system --no-create-home --disabled-password --shell /bin/bash user

WORKDIR /opt/ska-src-api-global-execution
ENV APP_ROOT_PATH /opt/ska-src-api-global-execution

COPY --chown=user pyproject.toml .
COPY --chown=user poetry.lock .

# # install dependencies via poetry
RUN poetry lock

COPY --chown=user . .

RUN poetry install --no-root

EXPOSE 8000

# Use ENTRYPOINT for the fixed part of the command
ENTRYPOINT ["/bin/bash"]

# Use CMD for the default script that can be overridden
CMD ["etc/api/run.sh"]