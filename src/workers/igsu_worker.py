from celery_worker import celery_app


@celery_app.task(name="src.workers.igsu_worker.sync_igsu_alerts")
def sync_igsu_alerts() -> dict[str, str]:
    return {
        "source": "https://dse.md/",
        "status": "placeholder",
    }

