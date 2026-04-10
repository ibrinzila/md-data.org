from celery_worker import celery_app


@celery_app.task(name="src.workers.nbs_worker.sync_nbs_tables")
def sync_nbs_tables() -> dict[str, str]:
    return {
        "source": "https://statbank.statistica.md/",
        "status": "placeholder",
    }

