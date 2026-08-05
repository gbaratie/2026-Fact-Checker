# Fact-Checker Présidentielle 2026

Collecte et exploration structurée des données sur les candidats à la présidentielle française 2026 : interviews YouTube, votes parlementaires et articles de presse.

## Architecture

- **Backend** : Python 3.12, FastAPI, SQLAlchemy, Alembic — hébergé sur [Render](https://render.com)
- **Base de données** : PostgreSQL sur [Neon](https://neon.tech)
- **Frontend** : React + Vite — hébergé sur GitHub Pages
- **Ingestion** : GitHub Actions quotidien (6h UTC)

## Sources de données

| Type | Source | Connecteur |
|------|--------|------------|
| Interviews | YouTube Data API v3 + transcripts | `app/connectors/youtube.py` |
| Votes | [CLAIR.vote](https://clair.vote) (Assemblée + Sénat) + open data AN | `app/connectors/parliament.py` |
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
# Tout (YouTube + votes + presse)
make ingest

# Votes Assemblée uniquement (CLAIR.vote)
make ingest-votes
```

## API

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Santé de l'API et de la DB |
| `GET /stats` | Compteurs légers (accueil) |
| `GET /candidates` | Liste des candidats |
| `GET /candidates/{slug}` | Détail avec compteurs + stats de vote |
| `GET /candidates/{slug}/interviews` | Interviews paginées |
| `GET /candidates/{slug}/votes` | Votes parlementaires paginés (`?chamber=assemblee\|senat`) |
| `GET /candidates/{slug}/articles` | Articles paginés |
| `GET /candidates/{slug}/programs` | Documents de programme paginés |
| `GET /candidates/{slug}/claims` | Positions structurées (claims) |
| `GET /candidates/{slug}/coherence` | Cohérence déclaration ↔ vote par thème |
| `GET /topics` | Référentiel de thèmes |
| `GET /groups` | Groupes parlementaires (AN + Sénat) |
| `GET /groups/{slug}` | Détail groupe + membres + stats |
| `GET /parties` | Agrégation par parti politique |
| `GET /parties/{party}` | Détail parti + candidats |
| `GET /ingestion/runs` | Historique des collectes |
| `POST /ingestion/trigger` | Déclenchement manuel (header `X-Ingestion-Secret`) |
| `POST /candidates` | Créer un candidat (header `X-Ingestion-Secret`) |
| `PATCH /candidates/{slug}` | Modifier un candidat (header `X-Ingestion-Secret`) |
| `DELETE /candidates/{slug}` | Supprimer un candidat (header `X-Ingestion-Secret`) |
| `POST /admin/seed-candidates` | Importer le seed YAML (header `X-Ingestion-Secret`) |

## Déploiement

### Neon

1. Créer un projet PostgreSQL sur [Neon](https://neon.tech)
2. Copier la connection string (`DATABASE_URL`)
3. Convertir le préfixe en `postgresql+asyncpg://` si nécessaire

### Render

1. Connecter le repo GitHub à Render
2. Appliquer le Blueprint [`render.yaml`](render.yaml) (API web uniquement, plan free)
3. Renseigner les variables d'environnement :
   - `DATABASE_URL` — connection string Neon
   - `YOUTUBE_API_KEY` — clé API Google Cloud
   - `CORS_ORIGINS` — URL GitHub Pages (ex. `https://votre-user.github.io`)

### GitHub Pages

1. Activer GitHub Pages (source : GitHub Actions) dans les paramètres du repo
2. Ajouter une variable de repo `VITE_API_URL` pointant vers l'URL Render de l'API
3. Le workflow `.github/workflows/deploy-frontend.yml` déploie automatiquement à chaque push sur `main`

### Ingestion (GitHub Actions)

Le workflow [`.github/workflows/ingest.yml`](.github/workflows/ingest.yml) tourne tous les jours à 6h UTC (et peut être lancé manuellement).

Secrets à ajouter dans **Settings → Secrets and variables → Actions** :

| Secret | Description |
|--------|-------------|
| `DATABASE_URL` | Connection string Neon (`postgresql+asyncpg://...`) |
| `YOUTUBE_API_KEY` | Clé API Google Cloud (optionnel) |

## Gestion des candidats

Interface web : **Gestion** (`/manage`) — ajouter / modifier (statut, parti, slug CLAIR) / supprimer des candidats. Protégé par le header `X-Ingestion-Secret` (= `INGESTION_SECRET` sur Render).

Pour peupler une base vide depuis le YAML :

```bash
make seed
# ou POST /admin/seed-candidates
```

Le matching des IDs parlementaires (Assemblée + Sénat) passe par CLAIR.vote.

API admin :

| Endpoint | Description |
|----------|-------------|
| `POST /candidates` | Créer un candidat (`X-Ingestion-Secret`) |
| `PATCH /candidates/{slug}` | Modifier parti, statut, slug CLAIR |
| `DELETE /candidates/{slug}` | Supprimer un candidat et ses données liées |
| `POST /admin/seed-candidates` | Importer/mettre à jour le YAML seed (CLI / API) |

## Structure du projet

```
backend/          API FastAPI + connecteurs + ingestion
frontend/         Interface d'exploration React
render.yaml       Blueprint Render (API web free)
docker-compose.yml Développement local
.github/workflows  CI, Pages, ingestion quotidienne
```

## Positions structurées & cohérence

Tables `topics`, `claims`, `vote_topics` : thèmes référentiels, positions déclaratives (stance + citation + source) et tagging des votes par thème.

| Endpoint | Description |
|----------|-------------|
| `GET /topics` | Liste des thèmes |
| `POST /admin/seed-topics` | Importer `seeds/topics.yaml` (`X-Ingestion-Secret`) |
| `GET /candidates/{slug}/claims` | Positions du candidat |
| `POST /candidates/{slug}/claims` | Créer une position (`X-Ingestion-Secret`) |
| `PATCH /claims/{id}` / `DELETE /claims/{id}` | Modifier / supprimer |
| `PUT /votes/{id}/topics` | Remplacer les thèmes d'un vote |
| `GET /candidates/{slug}/coherence` | Comparaison déclaration ↔ vote par thème |

`make seed` importe d'abord les thèmes, puis les candidats.

Statuts de cohérence : `aligned`, `conflict`, `mixed`, `claims_only`, `votes_only`, `abstention_only`.

## Phase 2 (suite)

- Extraction LLM des positions depuis transcripts / programmes
- Curation assistée puis revue humaine
- Dashboards analytiques
- Sources sociales (X, Instagram) après un volume suffisant de claims validés
