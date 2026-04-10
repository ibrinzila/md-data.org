# md-data.org

Moldova public data API starter built with FastAPI, Celery, Postgres, Redis, and Docker.

## Quick start

```bash
docker compose up --build
```

Open `http://localhost:8000/docs`.

## Included

- FastAPI app with versioned routers
- BNM exchange-rate sync endpoint
- procurement, statistics, weather, emergencies, and search endpoints
- Celery worker scaffold
- Postgres and Redis services
- CI workflow

