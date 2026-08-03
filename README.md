# Fact-Checker Présidentielle 2026

Collecte et exploration structurée des données sur les candidats à la présidentielle française 2026 : interviews YouTube, votes parlementaires et articles de presse.

## Architecture

- **Backend** : Python 3.12, FastAPI, SQLAlchemy, Alembic — hébergé sur [Render](https://render.com)
- **Base de données** : PostgreSQL sur [Neon](https://neon.tech)
- **Frontend** : React + Vite — hébergé sur GitHub Pages
- **Ingestion** : Cron Render quotidien (6h UTC)

## Sources de données

| Type | Source | Connecteur |
|------|--------|------------|
| Interviews | YouTube Data API v3 + transcripts | `app/connectors/youtube.py` |
| Votes | [CLAIR.vote](https://clair.vote/api) + open data AN | `app/connectors/parliament.py` |
| Articles | Flux RSS presse FR (Le Monde, Figaro, Libé, Mediapart, etc.) — provenance `feed_url` stockée | `app/connectors/press_rss.py` |
| Programmes | Documents curated (sites/PDF officiels) dans `seeds/candidates.yaml` | `app/connectors/programs.py` |

## Démarrage local

### Prérequis

- Docker & Docker Compose
- Node.js 20+
- Python 3.12+ (optionnel si Docker uniquement)

### 1. Configuration

```bash
cp .env.example .env
# Renseigner YOUTUBE_API_KEY si disponible
```

### 2. Lancer les services

```bash
make up
make migrate
make seed
```

L'API est disponible sur http://localhost:8000 (docs : http://localhost:8000/docs).

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Interface sur http://localhost:5173.

### 4. Lancer une ingestion

```bash
make ingest
```

## API

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Santé de l'API et de la DB |
| `GET /candidates` | Liste des candidats |
| `GET /candidates/{slug}` | Détail avec compteurs |
| `GET /candidates/{slug}/interviews` | Interviews paginées |
| `GET /candidates/{slug}/votes` | Votes parlementaires paginés |
| `GET /candidates/{slug}/articles` | Articles paginés |
| `GET /candidates/{slug}/programs` | Documents de programme paginés |
| `GET /ingestion/runs` | Historique des collectes |
| `POST /ingestion/trigger` | Déclenchement manuel (header `X-Ingestion-Secret`) |

## Déploiement

### Neon

1. Créer un projet PostgreSQL sur [Neon](https://neon.tech)
2. Copier la connection string (`DATABASE_URL`)
3. Convertir le préfixe en `postgresql+asyncpg://` si nécessaire

### Render

1. Connecter le repo GitHub à Render
2. Appliquer le Blueprint [`render.yaml`](render.yaml)
3. Renseigner les variables d'environnement :
   - `DATABASE_URL` — connection string Neon
   - `YOUTUBE_API_KEY` — clé API Google Cloud
   - `CORS_ORIGINS` — URL GitHub Pages (ex. `https://votre-user.github.io`)

### GitHub Pages

1. Activer GitHub Pages (source : GitHub Actions) dans les paramètres du repo
2. Ajouter une variable de repo `VITE_API_URL` pointant vers l'URL Render de l'API
3. Le workflow `.github/workflows/deploy-frontend.yml` déploie automatiquement à chaque push sur `main`

## Gestion des candidats

Éditer [`backend/seeds/candidates.yaml`](backend/seeds/candidates.yaml) puis :

```bash
make seed
```

Le script tente un matching automatique des IDs parlementaires via CLAIR.vote.

## Structure du projet

```
backend/          API FastAPI + connecteurs + ingestion
frontend/         Interface d'exploration React
render.yaml       Blueprint Render (API + cron)
docker-compose.yml Développement local
```

## Phase 2 (prévu)

- Extraction des positions de programme depuis les transcripts
- Détection d'incohérences entre votes, déclarations et articles
- Dashboards analytiques
