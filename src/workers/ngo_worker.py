from celery_worker import celery_app

from src.services.registry_ingest import ENTITY_ALIASES, sync_registry_entities


@celery_app.task(name="src.workers.ngo_worker.sync_ngos")
def sync_ngos() -> dict[str, int]:
    return sync_registry_entities(entity_type="ngo", queries=ENTITY_ALIASES["ngo"]["queries"])
