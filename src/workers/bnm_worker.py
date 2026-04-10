from datetime import date

from celery_worker import celery_app


@celery_app.task(name="src.workers.bnm_worker.sync_bnm_rates")
def sync_bnm_rates() -> dict[str, str]:
    return {
        "source": "http://www.bnm.md/en/official_exchange_rates",
        "date": date.today().isoformat(),
        "status": "placeholder",
    }

