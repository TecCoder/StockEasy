.PHONY: install dev test lint format migrate seed backup
install:
	python -m venv .venv
	.venv/bin/python -m pip install -e './backend[dev]'
	cd frontend && npm ci
dev:
	@echo "Run backend: cd backend && ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --no-access-log"
	@echo "Run frontend in a second terminal: cd frontend && npm run dev"
test:
	cd backend && ../.venv/bin/python -m pytest
	cd frontend && npm test
lint:
	cd backend && ../.venv/bin/python -m ruff check . && ../.venv/bin/python -m mypy app
	cd frontend && npm run lint && npm run typecheck
format:
	.venv/bin/python -m ruff format backend
	cd frontend && npm run format
migrate:
	mkdir -p data
	cd backend && ../.venv/bin/python -m alembic upgrade head
seed:
	cd backend && ../.venv/bin/python -m app.cli create-user --username $(USER)
backup:
	.venv/bin/python scripts/backup.py backup
