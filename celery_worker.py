import os

from celery import Celery
from celery.schedules import crontab

from src.workers.base_worker import BaseWorker  # noqa: F401

celery_app = Celery(
    "md_data_workers",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
)
celery_app.conf.task_routes = {"src.workers.*": {"queue": "default"}}
celery_app.conf.timezone = "Europe/Chisinau"
celery_app.conf.enable_utc = True
celery_app.conf.beat_schedule = {
    "sync-ckan-full-daily": {
        "task": "src.workers.ckan_full_worker.sync_ckan_full",
        "schedule": crontab(minute=20, hour=1),
    },
    "sync-companies-monthly": {
        "task": "src.workers.company_worker.sync_companies",
        "schedule": crontab(minute=0, hour=2, day_of_month="1"),
    },
    "sync-ngos-monthly": {
        "task": "src.workers.ngo_worker.sync_ngos",
        "schedule": crontab(minute=30, hour=2, day_of_month="1"),
    },
    "sync-monitorul-daily": {
        "task": "src.workers.legislation_worker.sync_monitorul",
        "schedule": crontab(minute=0, hour=3),
    },
    "sync-geospatial-weekly": {
        "task": "src.workers.geospatial_worker.sync_geospatial",
        "schedule": crontab(minute=15, hour=4, day_of_week="sun"),
    },
}

# Import worker modules so the task decorators register against celery_app.
from src.workers import bnm_worker, ckan_full_worker, ckan_worker, company_worker, eu_funds_worker, geospatial_worker, igsu_worker, legislation_worker, meteo_worker, mtender_worker, nbs_worker, ngo_worker  # noqa: E402,F401
