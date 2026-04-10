from celery_worker import celery_app

from src.services.registry_ingest import ENTITY_ALIASES, sync_registry_entities


@celery_app.task(name="src.workers.company_worker.sync_companies")
def sync_companies() -> dict[str, int]:
    return sync_registry_entities(entity_type="company", queries=ENTITY_ALIASES["company"]["queries"])
