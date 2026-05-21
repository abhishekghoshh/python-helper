# FastAPI TODO Service

<p align="center">
  <img src="https://img.shields.io/badge/python-3.14-blue" alt="Python 3.14">
  <img src="https://img.shields.io/badge/fastapi-%3E=0.100-green" alt="FastAPI">
  <img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="License">
</p>

---

A modern TODO service for learning Python with FastAPI, SQLModel, and clean architecture. Includes Docker, Helm, and CI/CD ready setup.

---

## 🚀 Features
- FastAPI backend with async support
- SQLModel for ORM and migrations
- Redis caching
- Clean architecture (Routers, Services, Repositories)
- Docker & Docker Compose for local dev
- Helm charts for Kubernetes deployment
- Poetry for dependency management
- Makefile for common tasks
- Linting, formatting, and tests included

## 📦 Project Setup & Dependencies

```bash
# Create project and enter directory
poetry new fastapi-todo-service
cd fastapi-todo-service

# Set Python version
poetry env use python3.14

# Activate environment
eval $(poetry env activate)

# Install dependencies
poetry lock
poetry install

# Add main dependencies
poetry add fastapi "uvicorn[standard]" httpx sqlmodel asyncpg psycopg2-binary redis aioredis pydantic-settings "passlib[bcrypt]" "pwdlib[argon2]" aiofiles

# Add development dependencies
poetry add --group dev pytest pytest-asyncio httpx black ruff httptest
```

## 🏗️ Architecture Overview

This project follows clean architecture, splitting components by responsibility:

```
[Client] → [Routers/Controllers] → [Services] → [Repositories] → [Database/Cache]
```

- **Routers**: Serialization, parsing, HTTP parameter handling
- **Services**: Domain logic, orchestration, transactional caching
- **Repositories**: SQLModel abstraction and DB access

## 🖥️ Local Development

Ensure [Poetry](https://python-poetry.org/) is installed.

```bash
# Install all dependencies
make install

# (Optional) Set environment variables
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/todo_db"

# Start the application
make run
```

## 🧹 Linting & Formatting

Run static analysis and formatting before committing:

```bash
# Format code
make format
# Lint code
make lint
```

## 🧪 Testing

Run all tests:

```bash
make test
```

## 🐳 Docker Compose: Local Production Testing

Spin up the full stack (API, Postgres, Redis) locally:

```bash
# Start all services
make up
# Tear down and clean up
make down
```

## ☸️ Helm: Kubernetes Deployment

Deploy to a Kubernetes cluster using Helm:

```bash
# Update chart dependencies (Postgres, Redis)
helm dependency update ./helm/fastapi-todo-service

# Install or upgrade the release
helm upgrade --install stable-release ./helm/fastapi-todo-service
```

## 📁 Project Structure

```
fastapi-todo-service/
├── src/
│   └── fastapi_todo_service/
│       ├── api/v1/         # Routers
│       ├── core/           # Config, DB, Redis, Logger
│       ├── models/         # Pydantic/SQLModel models
│       ├── repositories/   # Data access
│       ├── services/       # Business logic
│       └── utils/          # Utilities (security, etc)
├── tests/                  # Tests
├── charts/helm/            # Helm charts
├── Dockerfile              # Container build
├── docker-compose.yml      # Local stack
├── Makefile                # Common tasks
├── pyproject.toml          # Poetry config
└── README.md
```

## 🙌 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

This project is licensed under the MIT License.