.PHONY: up down migrate seed ingest ingest-votes test lint

up:
	docker compose up -d

down:
	docker compose down

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m app.seeds.seed_topics && python -m app.seeds.seed_candidates

ingest:
	cd backend && python -m app.ingestion.run

ingest-votes:
	cd backend && python -m app.ingestion.run_votes

test:
	cd backend && pytest

lint:
	cd backend && ruff check app tests
