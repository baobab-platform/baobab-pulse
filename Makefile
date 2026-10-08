.PHONY: sync lint format typecheck test test-all security build run migrate rebuild-projection compose-up compose-down clean

sync:
	uv sync --all-groups

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy src

test:
	uv run pytest -m "not provider"

test-all:
	uv run pytest

security:
	uv run --group security bandit -c bandit.yaml -r src
	uv run --group security pip-audit

build:
	docker build -t baobab-pulse:local .

run:
	uv run uvicorn baobab_pulse.api.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	uv run python scripts/migrate.py

rebuild-projection:
	uv run python scripts/rebuild_projection.py

compose-up:
	docker compose up --build

compose-down:
	docker compose down -v

clean:
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
	rm -rf .mypy_cache .ruff_cache .pytest_cache
