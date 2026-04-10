from celery_worker import celery_app


@celery_app.task(name="src.workers.meteo_worker.sync_meteo_forecast")
def sync_meteo_forecast() -> dict[str, str]:
    return {
        "source": "https://meteo.md/",
        "status": "placeholder",
    }

