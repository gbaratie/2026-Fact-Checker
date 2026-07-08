# Instructions pour les agents

## Cursor Cloud — instructions spécifiques

L'environnement cloud est configuré via `.cursor/environment.json`. Au démarrage :

1. **install** : installe les dépendances Python (`backend[dev]`) et Node (`frontend`)
2. **start** : lance Docker, démarre PostgreSQL via `docker compose`, applique les migrations Alembic
3. **terminals** : démarre l'API FastAPI (port 8000) et le frontend Vite (port 5173)

### Commandes utiles

```bash
# Santé de l'API
curl http://localhost:8000/health

# Peupler les candidats (après migrate)
make seed

# Lancer une ingestion manuelle
make ingest

# Tests backend
make test

# Lint backend
make lint
```

### Variables d'environnement

Copier `.env.example` vers `.env` (fait automatiquement à l'install). Secrets à configurer dans le dashboard Cursor (onglet Secrets) :

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Par défaut : Postgres local via docker-compose. En prod : Neon (`postgresql+asyncpg://...`) |
| `YOUTUBE_API_KEY` | Clé API YouTube Data v3 (optionnelle en dev) |
| `INGESTION_SECRET` | Secret pour `POST /ingestion/trigger` |
| `CORS_ORIGINS` | Origines autorisées (ex. `http://localhost:5173`) |
| `VITE_API_URL` | URL de l'API pour le frontend (ex. `http://localhost:8000`) |

### Architecture

- **Backend** : FastAPI + SQLAlchemy async, port 8000
- **Frontend** : React + Vite, port 5173
- **Base de données** : PostgreSQL 16 (docker-compose en dev, Neon en prod)
- **Déploiement prod** : Render (API + cron) + GitHub Pages (frontend) — voir `render.yaml` et `README.md`

### Tests avant PR

```bash
make test
cd frontend && npm run build
```
