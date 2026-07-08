.PHONY: up down migrate seed ingest test lint

up:
	docker compose up -d

down:
	docker compose down

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m app.seeds.seed_candidates

ingest:
	cd backend && python -m app.ingestion.run

test:
	cd backend && pytest

lint:
	cd backend && ruff check app tests
