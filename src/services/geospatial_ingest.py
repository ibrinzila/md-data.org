from __future__ import annotations

import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.api.v1.schemas import GeoLayer
from src.db import session as db_session
from src.db.models import CKANDatasetRecord, GeoLayerRecord
from src.services.ckan_ingest import search_packages
from src.services.ingest_utils import clean_text, json_safe, normalize_query

logger = logging.getLogger(__name__)

GEO_QUERIES = ["geospatial", "cadastre", "geographic names", "geo", "maps", "land"]


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


def _layer_to_schema(record: GeoLayerRecord) -> GeoLayer:
    return GeoLayer(
        layer_key=record.layer_key,
        title=record.title,
        description=record.description,
        source_type=record.source_type,
        source_url=record.source_url,
        metadata=dict(record.layer_metadata or {}),
    )


def _upsert_layer(session: Session, *, layer_key: str, title: str, description: str | None, source_type: str, source_url: str, metadata: dict[str, Any]) -> GeoLayerRecord:
    record = session.scalar(select(GeoLayerRecord).where(GeoLayerRecord.layer_key == layer_key))
    if record is None:
        record = GeoLayerRecord(layer_key=layer_key, title=title, source_type=source_type, source_url=source_url)
    record.title = title
    record.description = description
    record.source_type = source_type
    record.source_url = source_url
    record.layer_metadata = metadata
    record.raw_payload = json_safe(metadata)
    record.synced_at = datetime.now(timezone.utc)
    session.add(record)
    return record


def sync_geospatial_database(*, session: Session | None = None, package_limit: int = 25) -> dict[str, int]:
    ensure_schema()
    with _session_scope(session) as db:
        created = 0
        searched = 0
        seen: set[str] = set()
        for query in GEO_QUERIES:
            try:
                packages = search_packages(query, rows=package_limit)
            except Exception:
                logger.exception("Geospatial package search failed for %s", query)
                continue
            for package in packages:
                searched += 1
                dataset_id = clean_text(package.get("name") or package.get("id") or "")
                if not dataset_id or dataset_id in seen:
                    continue
                seen.add(dataset_id)
                title = clean_text(package.get("title") or dataset_id)
                description = clean_text(package.get("notes") or package.get("organization", {}).get("title") or "")
                source_url = clean_text(package.get("url") or f"https://dataset.gov.md/en/dataset/{dataset_id}")
                _upsert_layer(
                    db,
                    layer_key=dataset_id,
                    title=title,
                    description=description,
                    source_type="ckan",
                    source_url=source_url,
                    metadata={
                        "dataset_id": dataset_id,
                        "tags": [tag.get("name") for tag in package.get("tags") or []],
                        "organization": (package.get("organization") or {}).get("title"),
                        "resources": package.get("resources") or [],
                    },
                )
                created += 1
        db.commit()
        return {"layers": created, "searched": searched}


def _query_layers(db: Session, query: str | None = None) -> list[GeoLayerRecord]:
    stmt = select(GeoLayerRecord)
    if query:
        terms = f"%{normalize_query(query)}%"
        stmt = stmt.where(
            or_(
                GeoLayerRecord.title.ilike(terms),
                GeoLayerRecord.description.ilike(terms),
                GeoLayerRecord.layer_key.ilike(terms),
                GeoLayerRecord.source_type.ilike(terms),
            )
        )
    stmt = stmt.order_by(GeoLayerRecord.updated_at.desc(), GeoLayerRecord.title.asc())
    return list(db.scalars(stmt).all())


def list_layers(*, query: str | None = None, sync_if_empty: bool = True, session: Session | None = None) -> list[GeoLayer]:
    ensure_schema()
    with _session_scope(session) as db:
        if sync_if_empty and not db.scalar(select(func.count()).select_from(GeoLayerRecord)):
            try:
                sync_geospatial_database(session=db)
            except Exception:
                logger.exception("Geospatial sync failed")
        return [_layer_to_schema(record) for record in _query_layers(db, query=query)]


def get_layer(layer_key: str, *, sync_if_missing: bool = True, session: Session | None = None) -> GeoLayer | None:
    ensure_schema()
    with _session_scope(session) as db:
        record = db.scalar(select(GeoLayerRecord).where(GeoLayerRecord.layer_key == layer_key))
        if record is None and sync_if_missing:
            try:
                sync_geospatial_database(session=db)
            except Exception:
                logger.exception("Geospatial sync failed for %s", layer_key)
            record = db.scalar(select(GeoLayerRecord).where(GeoLayerRecord.layer_key == layer_key))
        return _layer_to_schema(record) if record else None


def search_layers(query: str, *, session: Session | None = None) -> list[GeoLayer]:
    ensure_schema()
    with _session_scope(session) as db:
        return [_layer_to_schema(record) for record in _query_layers(db, query=query)]
