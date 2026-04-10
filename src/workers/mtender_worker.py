from celery_worker import celery_app


@celery_app.task(name="src.workers.mtender_worker.sync_mtender_tenders")
def sync_mtender_tenders() -> dict[str, str]:
    return {
        "source": "https://public.mtender.gov.md/tenders",
        "status": "placeholder",
    }

