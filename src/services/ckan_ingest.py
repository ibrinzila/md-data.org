from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.api.v1.schemas import CKANDataset
from src.db import session as db_session
from src.db.models import CKANDatasetRecord
from src.services.ingest_utils import clean_text, json_safe, parse_datetime, unique_list

logger = logging.getLogger(__name__)

CKAN_ACTION_BASE_URLS = (
    "https://dataset.gov.md/en/api/3/action",
    "https://date.gov.md/api/3/action",
)
CKAN_PORTAL_BASE_URLS = (
    "https://dataset.gov.md/en",
    "https://date.gov.md",
)
HTTP_HEADERS = {"User-Agent": "md-data.org/1.0 (+https://md-data.org)"}


@contextmanager
def _session_scope(session: Session | None = None):
    if session is not None:
        yield session
        return

    db = db_session.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema() -> None:
    db_session.create_schema()


def _client() -> httpx.Client:
    return httpx.Client(timeout=30.0, follow_redirects=True, headers=HTTP_HEADERS)


def _action_urls(action: str) -> list[str]:
    return [f"{base_url}/{action}" for base_url in CKAN_ACTION_BASE_URLS]


def _dataset_url(slug: str) -> str:
    return f"{CKAN_PORTAL_BASE_URLS[0]}/dataset/{slug}"


def _request_action(action: str, params: dict[str, Any] | None = None) -> Any:
    last_error: Exception | None = None
    with _client() as client:
        for url in _action_urls(action):
            try:
                response = client.get(url, params=params)
                if response.status_code == 404:
                    last_error = httpx.HTTPStatusError(
                        "Not Found",
                        request=response.request,
                        response=response,
                    )
                    continue
                response.raise_for_status()
                payload = response.json()
                if isinstance(payload, dict):
                    if "result" in payload:
                        return payload["result"]
                    return payload
                return payload
            except Exception as exc:
                last_error = exc
                continue
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"CKAN action failed for {action}")


def fetch_package_list() -> list[str]:
    return list(_request_action("package_list") or [])


def fetch_package_show(package_id: str) -> dict[str, Any]:
    return dict(_request_action("package_show", params={"id": package_id}) or {})


def search_packages(query: str, rows: int = 50) -> list[dict[str, Any]]:
    payload = _request_action("package_search", params={"q": query, "rows": rows})
    if isinstance(payload, dict):
        return list(payload.get("results") or [])
    return []


def _dataset_to_schema(record: CKANDatasetRecord) -> CKANDataset:
    return CKANDataset(
        dataset_id=record.dataset_id,
        title=record.title,
        slug=record.slug,
        notes=record.notes,
        organization=record.organization,
        tags=list(record.tags or []),
        resources=list(record.resources or []),
        source_url=record.source_url,
        source_modified_at=record.source_modified_at,
    )


def _upsert_dataset(session: Session, package: dict[str, Any]) -> CKANDatasetRecord | None:
    dataset_id = clean_text(package.get("name") or package.get("id") or "")
    if not dataset_id:
        return None

    title = clean_text(package.get("title") or dataset_id)
    slug = clean_text(package.get("name") or dataset_id)
    notes = clean_text(package.get("notes") or package.get("description") or "")
    org = package.get("organization") or {}
    organization = clean_text(org.get("title") or org.get("name") or "")
    tags = unique_list(clean_text(tag.get("name") or "") for tag in package.get("tags") or [])
    resources: list[dict[str, Any]] = []
    for resource in package.get("resources") or []:
      resources.append(
          {
              "id": clean_text(resource.get("id") or ""),
              "name": clean_text(resource.get("name") or resource.get("title") or ""),
              "format": clean_text(resource.get("format") or ""),
              "url": clean_text(resource.get("url") or ""),
              "mimetype": clean_text(resource.get("mimetype") or ""),
              "datastore_active": resource.get("datastore_active"),
          }
      )

    record = session.scalar(select(CKANDatasetRecord).where(CKANDatasetRecord.dataset_id == dataset_id))
    if record is None:
        record = CKANDatasetRecord(dataset_id=dataset_id, title=title, slug=slug, source_url=_dataset_url(slug))

    record.title = title
    record.slug = slug
    record.notes = notes or None
    record.organization = organization or None
    record.tags = tags
    record.resources = resources
    record.source_url = clean_text(package.get("url") or _dataset_url(slug))
    record.source_modified_at = parse_datetime(package.get("metadata_modified") or package.get("modified"))
    record.raw_payload = json_safe(package)
    record.synced_at = datetime.now(timezone.utc)
    session.add(record)
    return record


def sync_ckan_full_database(*, session: Session | None = None, package_limit: int | None = None) -> dict[str, int]:
    ensure_schema()
    with _session_scope(session) as db:
        package_ids = fetch_package_list()
        if package_limit is not None:
            package_ids = package_ids[:package_limit]

        counts = {"datasets": 0, "searched": len(package_ids)}
        for package_id in package_ids:
            try:
                package = fetch_package_show(package_id)
            except Exception:
                logger.exception("CKAN package fetch failed for %s", package_id)
                continue
            if _upsert_dataset(db, package):
                counts["datasets"] += 1

        db.commit()
        return counts


def _query_datasets(db: Session, query: str | None = None) -> list[CKANDatasetRecord]:
    stmt = select(CKANDatasetRecord)
    if query:
        terms = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                CKANDatasetRecord.title.ilike(terms),
                CKANDatasetRecord.slug.ilike(terms),
                CKANDatasetRecord.notes.ilike(terms),
                CKANDatasetRecord.organization.ilike(terms),
            )
        )
    stmt = stmt.order_by(CKANDatasetRecord.updated_at.desc(), CKANDatasetRecord.title.asc())
    return list(db.scalars(stmt).all())


def list_datasets(*, query: str | None = None, sync_if_empty: bool = True, session: Session | None = None) -> list[CKANDataset]:
    ensure_schema()
    with _session_scope(session) as db:
        if sync_if_empty and not db.scalar(select(func.count()).select_from(CKANDatasetRecord)):
            try:
                sync_ckan_full_database(session=db, package_limit=100)
            except Exception:
                logger.exception("CKAN sync failed")
        return [_dataset_to_schema(record) for record in _query_datasets(db, query=query)]


def get_dataset(dataset_id: str, *, sync_if_missing: bool = True, session: Session | None = None) -> CKANDataset | None:
    ensure_schema()
    with _session_scope(session) as db:
        record = db.scalar(select(CKANDatasetRecord).where(CKANDatasetRecord.dataset_id == dataset_id))
        if record is None and sync_if_missing:
            try:
                sync_ckan_full_database(session=db, package_limit=100)
            except Exception:
                logger.exception("CKAN sync failed for dataset %s", dataset_id)
            record = db.scalar(select(CKANDatasetRecord).where(CKANDatasetRecord.dataset_id == dataset_id))
        return _dataset_to_schema(record) if record else None


def search_datasets(query: str, *, session: Session | None = None) -> list[CKANDataset]:
    ensure_schema()
    with _session_scope(session) as db:
        return [_dataset_to_schema(record) for record in _query_datasets(db, query=query)]
