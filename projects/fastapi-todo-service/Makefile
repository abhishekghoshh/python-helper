.PHONY: install run lint format test up down

install:
	poetry install

run:
	poetry run uvicorn fastapi_todo_service.main:app --reload

lint:
	poetry run ruff check src/

format:
	poetry run ruff format app/

test:
	poetry run pytest

up:
	docker-compose up --build -d

down:
	docker-compose down