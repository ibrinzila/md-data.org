# md-data.org

Moldova public data API starter built with FastAPI, Celery, Postgres, Redis, and Docker.

## Quick start

```bash
docker compose up --build
```

Open `http://localhost:8000/docs`.
Open `http://localhost:8000/status` for the status dashboard.

For local development without Docker:

```bash
source .venv/bin/activate
uvicorn src.api.main:app --host 127.0.0.1 --port 8000
celery -A celery_worker.celery_app worker --loglevel=info
celery -A celery_worker.celery_app beat --loglevel=info --schedule=/tmp/md-data-celerybeat-schedule
```

## Included

- FastAPI app with versioned routers
- Status dashboard at `/status`
- BNM exchange-rate sync endpoint
- procurement, statistics, weather, emergencies, search, and EU funding endpoints
- CKAN datasets, company/NGO registers, legislation search, and geospatial layers
- Celery worker and beat scheduler scaffold
- Postgres and Redis services
- CI workflow

## New in this release

- MTender procurement expanded with OCDS-style procurement routes, raion filtering, statistics, and tender cross-references
- EU Funding module with `/v1/eu-funds/projects`, `/v1/eu-funds/statistics`, and a dedicated worker scaffold
- CKAN full sync worker plus source-specific workers for companies, NGOs, legislation, and geospatial layers
- Global search at `/v1/search` now spans CKAN datasets, registries, legislation, geospatial data, and the existing civic feeds
- Celery Beat now schedules CKAN, companies, NGOs, legislation, and geospatial syncs on a real cadence
