from celery import Celery

from src.workers.base_worker import BaseWorker  # noqa: F401

celery_app = Celery(
    "md_data_workers",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)
celery_app.conf.task_routes = {"src.workers.*": {"queue": "default"}}

# Import worker modules so the task decorators register against celery_app.
from src.workers import bnm_worker, ckan_full_worker, ckan_worker, company_worker, eu_funds_worker, geospatial_worker, igsu_worker, legislation_worker, meteo_worker, mtender_worker, nbs_worker, ngo_worker  # noqa: E402,F401
