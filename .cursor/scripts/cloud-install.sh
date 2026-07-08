#!/usr/bin/env bash
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"

echo "==> Installation des dépendances backend"
pip install --user -e "./backend[dev]"

echo "==> Installation des dépendances frontend"
npm ci --prefix frontend

if [[ ! -f .env ]]; then
  echo "==> Création de .env depuis .env.example"
  cp .env.example .env
fi

echo "==> Installation terminée"
