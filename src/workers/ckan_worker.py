from celery_worker import celery_app


@celery_app.task(name="src.workers.ckan_worker.sync_ckan_packages")
def sync_ckan_packages() -> dict[str, str]:
    return {
        "source": "https://dataset.gov.md/api/3/action/package_list",
        "status": "placeholder",
    }

