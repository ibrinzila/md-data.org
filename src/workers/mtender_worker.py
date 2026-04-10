from celery_worker import celery_app

from src.services.mtender_ingest import sync_mtender_database


@celery_app.task(name="src.workers.mtender_worker.sync_mtender_tenders")
def sync_mtender_tenders() -> dict[str, int]:
    return sync_mtender_database()
