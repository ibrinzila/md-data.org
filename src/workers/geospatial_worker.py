from celery_worker import celery_app

from src.services.geospatial_ingest import sync_geospatial_database


@celery_app.task(name="src.workers.geospatial_worker.sync_geospatial")
def sync_geospatial() -> dict[str, int]:
    return sync_geospatial_database()
