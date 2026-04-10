from celery_worker import celery_app

from src.services.legislation_ingest import sync_legislation_database


@celery_app.task(name="src.workers.legislation_worker.sync_monitorul")
def sync_monitorul() -> dict[str, int]:
    return sync_legislation_database()
