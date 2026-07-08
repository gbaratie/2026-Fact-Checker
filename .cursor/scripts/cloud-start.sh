#!/usr/bin/env bash
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"

echo "==> Démarrage du daemon Docker"
sudo service docker start

echo "==> Démarrage de PostgreSQL (docker compose)"
docker compose up -d db

echo "==> Attente de PostgreSQL..."
for _ in $(seq 1 60); do
  if docker compose exec -T db pg_isready -U factchecker >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! docker compose exec -T db pg_isready -U factchecker >/dev/null 2>&1; then
  echo "ERREUR: PostgreSQL n'est pas prêt après 60 secondes" >&2
  exit 1
fi

echo "==> Application des migrations"
(cd backend && alembic upgrade head)

echo "==> Environnement prêt (API: http://localhost:8000, frontend: http://localhost:5173)"
