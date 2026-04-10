from celery_worker import celery_app

from src.services.eu_funds_ingest import sync_eu_funds_database


@celery_app.task(name="src.workers.eu_funds_worker.sync_eu_funds")
def sync_eu_funds() -> dict[str, int]:
    return sync_eu_funds_database()
