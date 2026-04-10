from __future__ import annotations

import csv
import io
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.api.v1.schemas import RegistryEntity
from src.db import session as db_session
from src.db.models import RegistryEntityRecord
from src.services.ckan_ingest import fetch_package_show, search_packages
from src.services.ingest_utils import clean_text, json_safe, normalize_query, parse_datetime, unique_list

logger = logging.getLogger(__name__)

HTTP_HEADERS = {"User-Agent": "md-data.org/1.0 (+https://md-data.org)"}
ENTITY_ALIASES = {
    "company": {
        "queries": ["legal entities moldova", "state register legal entities", "idno company", "companies"],
        "type": "company",
    },
    "ngo": {
        "queries": ["non-profit organizations", "ngos", "civil society organizations", "non government organizations"],
        "type": "ngo",
    },
}


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


def _resource_text(url: str) -> str:
    with _client() as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def _parse_rows_from_resource(resource: dict[str, Any]) -> list[dict[str, Any]]:
    url = clean_text(resource.get("url") or "")
    if not url:
        return []
    fmt = normalize_query(clean_text(resource.get("format") or resource.get("mimetype") or ""))
    try:
        text = _resource_text(url)
    except Exception:
        logger.exception("Failed to fetch registry resource %s", url)
        return []

    if "json" in fmt or url.lower().endswith(".json"):
        try:
            payload = json.loads(text)
        except Exception:
            return []
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("result", "data", "records", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    if "csv" in fmt or "tsv" in fmt or url.lower().endswith((".csv", ".tsv")):
        delimiter = "\t" if "tsv" in fmt or url.lower().endswith(".tsv") else ","
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        return [dict(row) for row in reader]

    return []


def _first_value(row: dict[str, Any], aliases: Iterable[str]) -> str | None:
    normalized = {normalize_query(str(key)): value for key, value in row.items()}
    for alias in aliases:
        alias_normalized = normalize_query(alias)
        if alias_normalized in normalized:
            value = clean_text(str(normalized[alias_normalized]))
            if value:
                return value
    for key, value in row.items():
        key_normalized = normalize_query(str(key))
        if any(alias in key_normalized for alias in aliases):
            candidate = clean_text(str(value))
            if candidate:
                return candidate
    return None


def _infer_status(row: dict[str, Any], fallback: str) -> str:
    value = _first_value(row, ["status", "state", "active", "registration status"]) or fallback
    return clean_text(value) or fallback


def _infer_name(row: dict[str, Any], fallback: str) -> str:
    return _first_value(row, ["name", "company", "organization", "entity name", "title"]) or fallback


def _infer_identifier(row: dict[str, Any], fallback: str) -> tuple[str, str]:
    for label in ("idno", "id no", "registration number", "tax id", "fiscal code", "identifier", "code", "nif"):
        value = _first_value(row, [label])
        if value:
            return (label, value)
    return ("dataset_row", fallback)


def _entity_to_schema(record: RegistryEntityRecord) -> RegistryEntity:
    return RegistryEntity(
        entity_key=record.entity_key,
        entity_type=record.entity_type,
        entity_id=record.entity_id,
        name=record.name,
        status=record.status,
        description=record.description,
        raion=record.raion,
        locality=record.locality,
        identifier_label=record.identifier_label,
        identifier_value=record.identifier_value,
        source_dataset_id=record.source_dataset_id,
        source_url=record.source_url,
        cross_references=dict(record.cross_references or {}),
    )


def _upsert_entity(
    session: Session,
    *,
    entity_type: str,
    row: dict[str, Any],
    source_dataset_id: str,
    source_url: str,
    fallback_key: str,
    title_hint: str | None = None,
) -> RegistryEntityRecord:
    identifier_label, identifier_value = _infer_identifier(row, fallback_key)
    name = _infer_name(row, title_hint or identifier_value)
    entity_id = identifier_value or fallback_key
    entity_key = f"{entity_type}:{entity_id}"
    status = _infer_status(row, "active")
    raion = _first_value(row, ["raion", "district", "region", "rayon"]) or None
    locality = _first_value(row, ["locality", "city", "municipality", "village"]) or None
    description = clean_text(
        _first_value(row, ["description", "notes", "comment", "remarks"]) or title_hint or ""
    )

    record = session.scalar(select(RegistryEntityRecord).where(RegistryEntityRecord.entity_key == entity_key))
    if record is None:
        record = RegistryEntityRecord(
            entity_key=entity_key,
            entity_type=entity_type,
            entity_id=entity_id,
            name=name,
            source_dataset_id=source_dataset_id,
            source_url=source_url,
        )

    record.entity_type = entity_type
    record.entity_id = entity_id
    record.name = name
    record.status = status
    record.description = description or None
    record.raion = raion
    record.locality = locality
    record.identifier_label = identifier_label
    record.identifier_value = identifier_value
    record.source_dataset_id = source_dataset_id
    record.source_url = source_url
    record.cross_references = dict(record.cross_references or {})
    record.raw_payload = json_safe(row)
    record.synced_at = datetime.now(timezone.utc)
    session.add(record)
    return record


def sync_registry_entities(
    *,
    entity_type: str,
    queries: list[str],
    session: Session | None = None,
    package_limit: int = 10,
    resource_limit: int = 2,
) -> dict[str, int]:
    ensure_schema()
    counts = {"entities": 0, "packages": 0}

    with _session_scope(session) as db:
        seen_keys: set[str] = set()
        for query in queries:
            try:
                packages = search_packages(query, rows=package_limit)
            except Exception:
                logger.exception("Registry package search failed for %s", query)
                continue
            for package in packages:
                package_id = clean_text(package.get("name") or package.get("id") or "")
                if not package_id:
                    continue
                counts["packages"] += 1
                try:
                    detail = fetch_package_show(package_id)
                except Exception:
                    logger.exception("Registry package show failed for %s", package_id)
                    detail = package
                resources = detail.get("resources") or []
                matched_resources = [resource for resource in resources if clean_text(resource.get("url") or "")][:resource_limit]
                for index, resource in enumerate(matched_resources, start=1):
                    rows = _parse_rows_from_resource(resource)
                    if not rows:
                        continue
                    resource_url = clean_text(resource.get("url") or detail.get("url") or "")
                    title_hint = clean_text(detail.get("title") or package_id)
                    for row_index, row in enumerate(rows[:200], start=1):
                        record = _upsert_entity(
                            db,
                            entity_type=entity_type,
                            row=row,
                            source_dataset_id=package_id,
                            source_url=resource_url or f"https://date.gov.md/dataset/{package_id}",
                            fallback_key=f"{package_id}:{index}:{row_index}",
                            title_hint=title_hint,
                        )
                        if record.entity_key not in seen_keys:
                            counts["entities"] += 1
                            seen_keys.add(record.entity_key)

                if counts["entities"] == 0:
                    fallback_row = {
                        "idno": package_id,
                        "name": detail.get("title") or package_id,
                        "status": detail.get("state") or "active",
                        "description": detail.get("notes") or package.get("notes") or "",
                    }
                    record = _upsert_entity(
                        db,
                        entity_type=entity_type,
                        row=fallback_row,
                        source_dataset_id=package_id,
                        source_url=clean_text(detail.get("url") or f"https://date.gov.md/dataset/{package_id}"),
                        fallback_key=package_id,
                        title_hint=detail.get("title") or package_id,
                    )
                    if record.entity_key not in seen_keys:
                        counts["entities"] += 1
                        seen_keys.add(record.entity_key)

        db.commit()
        return counts


def _query_entities(db: Session, entity_type: str, query: str | None = None) -> list[RegistryEntityRecord]:
    stmt = select(RegistryEntityRecord).where(RegistryEntityRecord.entity_type == entity_type)
    if query:
        terms = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                RegistryEntityRecord.name.ilike(terms),
                RegistryEntityRecord.entity_id.ilike(terms),
                RegistryEntityRecord.identifier_value.ilike(terms),
                RegistryEntityRecord.status.ilike(terms),
                RegistryEntityRecord.description.ilike(terms),
                RegistryEntityRecord.raion.ilike(terms),
                RegistryEntityRecord.locality.ilike(terms),
                RegistryEntityRecord.source_dataset_id.ilike(terms),
            )
        )
    stmt = stmt.order_by(RegistryEntityRecord.updated_at.desc(), RegistryEntityRecord.name.asc())
    return list(db.scalars(stmt).all())


def list_entities(entity_type: str, *, query: str | None = None, sync_if_empty: bool = True, session: Session | None = None) -> list[RegistryEntity]:
    ensure_schema()
    with _session_scope(session) as db:
        if sync_if_empty and not db.scalar(
            select(func.count()).select_from(RegistryEntityRecord).where(RegistryEntityRecord.entity_type == entity_type)
        ):
            try:
                sync_registry_entities(
                    entity_type=entity_type,
                    queries=ENTITY_ALIASES[entity_type]["queries"],
                    session=db,
                )
            except Exception:
                logger.exception("Registry sync failed for %s", entity_type)
        return [_entity_to_schema(record) for record in _query_entities(db, entity_type, query=query)]


def get_entity(entity_type: str, entity_id: str, *, sync_if_missing: bool = True, session: Session | None = None) -> RegistryEntity | None:
    ensure_schema()
    with _session_scope(session) as db:
        record = db.scalar(
            select(RegistryEntityRecord).where(
                RegistryEntityRecord.entity_type == entity_type,
                RegistryEntityRecord.entity_id == entity_id,
            )
        )
        if record is None and sync_if_missing:
            try:
                sync_registry_entities(
                    entity_type=entity_type,
                    queries=[entity_id] + ENTITY_ALIASES.get(entity_type, {}).get("queries", []),
                    session=db,
                )
            except Exception:
                logger.exception("Registry sync failed for %s / %s", entity_type, entity_id)
            record = db.scalar(
                select(RegistryEntityRecord).where(
                    RegistryEntityRecord.entity_type == entity_type,
                    RegistryEntityRecord.entity_id == entity_id,
                )
            )
        return _entity_to_schema(record) if record else None
