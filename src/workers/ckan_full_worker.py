from celery_worker import celery_app

from src.services.ckan_ingest import sync_ckan_full_database


@celery_app.task(name="src.workers.ckan_full_worker.sync_ckan_full")
def sync_ckan_full() -> dict[str, int]:
    return sync_ckan_full_database()
