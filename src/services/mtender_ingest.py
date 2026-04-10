from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.api.v1.schemas import (
    BuyerReference,
    OCDSAmount,
    Location,
    ProcurementAward,
    ProcurementBudget,
    ProcurementContract,
    ProcurementPlan,
    ProcurementStatistics,
    ProcurementTender,
)
from src.db import session as db_session
from src.db.models import (
    ProcurementAwardRecord,
    ProcurementBudgetRecord,
    ProcurementContractRecord,
    ProcurementPlanRecord,
    ProcurementTenderRecord,
)
from src.services.cross_reference import rebuild_cross_references
from src.services.ingest_utils import clean_text, infer_sector, json_safe, parse_bool, parse_datetime, unique_list

logger = logging.getLogger(__name__)

MTENDER_TENDERS_URL = "https://mtender.gov.md/search/tenders"
MTENDER_CONTRACTS_URL = "https://mtender.gov.md/search/contracts"
MTENDER_BUDGETS_URL = "https://mtender.gov.md/search/budgets"
MTENDER_PLANS_URL = "https://mtender.gov.md/search/plans"
MTENDER_DETAIL_URL = "https://public.mtender.gov.md/tenders/{ocid}"

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


def _search_url(collection: str) -> str:
    return {
        "tenders": MTENDER_TENDERS_URL,
        "contracts": MTENDER_CONTRACTS_URL,
        "budgets": MTENDER_BUDGETS_URL,
        "plans": MTENDER_PLANS_URL,
    }[collection]


def _search_params(collection: str, page: int, page_size: int, query: str | None = None) -> dict[str, Any]:
    params: dict[str, Any] = {"page": page, "pageSize": page_size}
    if collection == "tenders":
        params["proceduresOwnerships"] = json.dumps(["government"])
    if query:
        params["query"] = query
    return params


def fetch_mtender_collection(collection: str, page: int = 1, page_size: int = 10, query: str | None = None) -> dict[str, Any]:
    with _client() as client:
        response = client.get(_search_url(collection), params=_search_params(collection, page, page_size, query))
        response.raise_for_status()
        return response.json()


def fetch_mtender_detail(ocid: str) -> dict[str, Any]:
    with _client() as client:
        response = client.get(MTENDER_DETAIL_URL.format(ocid=ocid))
        response.raise_for_status()
        return response.json()


def _choose_release(detail_payload: dict[str, Any]) -> dict[str, Any]:
    records = detail_payload.get("records") or []
    releases = [record.get("compiledRelease") for record in records if isinstance(record, dict) and record.get("compiledRelease")]
    if not releases:
        return {}
    return max(releases, key=lambda release: len(release))


def _first_party_value(release: dict[str, Any], key: str) -> str | None:
    parties = release.get("parties") or []
    for party in parties:
        address = party.get("address") or {}
        details = address.get("addressDetails") or {}
        region = details.get("region") or {}
        locality = details.get("locality") or {}
        if key == "raion" and region.get("description"):
            return clean_text(region.get("description"))
        if key == "city" and locality.get("description"):
            return clean_text(locality.get("description"))
    return None


def _tender_amount(tender: dict[str, Any], planning: dict[str, Any], summary: dict[str, Any]) -> tuple[float | None, str]:
    value = tender.get("value") or {}
    if not isinstance(value, dict) or not value:
        value = (planning.get("budget") or {}).get("amount") or {}
    if not isinstance(value, dict) or not value:
        amount = summary.get("amount")
        currency = summary.get("currency") or "MDL"
        return (float(amount) if amount is not None else None, currency)
    amount = value.get("amount")
    currency = value.get("currency") or summary.get("currency") or "MDL"
    return (float(amount) if amount is not None else None, currency)


def _upsert_tender(session: Session, summary: dict[str, Any], detail_payload: dict[str, Any]) -> ProcurementTenderRecord | None:
    release = _choose_release(detail_payload)
    tender = release.get("tender") or {}
    planning = release.get("planning") or {}
    procuring_entity = tender.get("procuringEntity") or {}
    classification = tender.get("classification") or {}
    source_ocid = clean_text(summary.get("entityId") or summary.get("id") or release.get("ocid") or "")
    if not source_ocid:
        return None

    title = clean_text(tender.get("title") or summary.get("title") or classification.get("description") or source_ocid)
    description = clean_text(tender.get("description") or summary.get("description") or classification.get("description") or "")
    status = clean_text(summary.get("procedureStatus") or tender.get("status") or "unknown") or "unknown"
    status_detail = clean_text(tender.get("statusDetails")) or None
    published_at = (
        parse_datetime(summary.get("modifiedDate"))
        or parse_datetime(release.get("date"))
        or parse_datetime(detail_payload.get("publishedDate"))
        or datetime.now(timezone.utc)
    )
    amount, currency = _tender_amount(tender, planning, summary)
    buyer_id = clean_text(procuring_entity.get("id") or summary.get("buyerName") or source_ocid)
    buyer_name = clean_text(procuring_entity.get("name") or summary.get("buyerName") or buyer_id)
    raion = clean_text(summary.get("buyerRegion") or _first_party_value(release, "raion") or "")
    city = clean_text(_first_party_value(release, "city") or "")
    buyer_sector = infer_sector(
        title,
        description,
        buyer_name,
        classification.get("description"),
        tender.get("mainProcurementCategory"),
    )
    procurement_method = clean_text(tender.get("procurementMethodDetails") or tender.get("procurementMethod")) or None
    procedure_type = clean_text(summary.get("procedureType") or tender.get("procurementMethodDetails") or tender.get("procurementMethod")) or None
    classification_code = clean_text(classification.get("id")) or None
    classification_description = clean_text(classification.get("description")) or None
    source_modified_at = parse_datetime(summary.get("modifiedDate"))

    record = session.scalar(select(ProcurementTenderRecord).where(ProcurementTenderRecord.ocid == source_ocid))
    if record is None:
        record = ProcurementTenderRecord(ocid=source_ocid, source_url=MTENDER_DETAIL_URL.format(ocid=source_ocid))

    record.title = title
    record.description = description or None
    record.status = status
    record.status_detail = status_detail
    record.date_published = published_at
    record.amount = amount
    record.currency = currency
    record.raion = raion or None
    record.city = city or None
    record.buyer_id = buyer_id
    record.buyer_name = buyer_name
    record.buyer_sector = buyer_sector
    record.procurement_method = procurement_method
    record.procedure_type = procedure_type
    record.classification_code = classification_code
    record.classification_description = classification_description
    record.source_url = MTENDER_DETAIL_URL.format(ocid=source_ocid)
    record.source_collection = "tenders"
    record.source_modified_at = source_modified_at

    cross_references = dict(record.cross_references or {})
    cross_references.setdefault("eu_project_ids", [])
    cross_references["procurement_method"] = procurement_method
    cross_references["procedure_type"] = procedure_type
    cross_references["main_category"] = tender.get("mainProcurementCategory")
    record.cross_references = cross_references
    record.raw_payload = {"summary": json_safe(summary), "release": json_safe(release), "detail": json_safe(detail_payload)}
    record.synced_at = datetime.now(timezone.utc)

    session.add(record)
    return record


def _upsert_award_or_contract_record(
    session: Session,
    item: dict[str, Any],
    *,
    kind: str,
) -> ProcurementAwardRecord | ProcurementContractRecord | None:
    source_ocid = clean_text(item.get("id") or item.get("entityId") or "")
    tender_ocid = clean_text(item.get("entityId") or source_ocid)
    if not source_ocid or not tender_ocid:
        return None

    title = clean_text(item.get("title") or item.get("description") or source_ocid)
    description = clean_text(item.get("description") or title)
    status = clean_text(item.get("procedureStatus") or (item.get("tags") or ["published"])[0] or "published") or "published"
    amount = item.get("amount")
    currency = clean_text(item.get("currency") or "MDL") or "MDL"
    raion = clean_text(item.get("buyerRegion") or "") or None
    buyer_name = clean_text(item.get("buyerName") or "") or None
    buyer_sector = infer_sector(title, description, buyer_name, raion)
    source_modified_at = parse_datetime(item.get("modifiedDate"))
    tags = [clean_text(tag) for tag in (item.get("tags") or []) if clean_text(tag)]
    supplier_name = clean_text(item.get("supplierName") or item.get("winnerName") or item.get("awardeeName") or "") or None

    if kind == "award":
        record = session.scalar(select(ProcurementAwardRecord).where(ProcurementAwardRecord.ocid == source_ocid))
        if record is None:
            record = ProcurementAwardRecord(
                ocid=source_ocid,
                tender_ocid=tender_ocid,
                title=title,
                status=status,
                source_url=MTENDER_CONTRACTS_URL,
            )
        record.tender_ocid = tender_ocid
        record.title = title
        record.status = status
        record.amount = float(amount) if amount is not None else None
        record.currency = currency
        record.supplier_name = supplier_name
        record.buyer_name = buyer_name
        record.buyer_sector = buyer_sector
        record.raion = raion
        record.source_url = MTENDER_CONTRACTS_URL
        record.source_collection = "contracts"
        record.source_modified_at = source_modified_at
        record.tags = tags
        record.raw_payload = item
        record.synced_at = datetime.now(timezone.utc)
        session.add(record)
        return record

    record = session.scalar(select(ProcurementContractRecord).where(ProcurementContractRecord.ocid == source_ocid))
    if record is None:
        record = ProcurementContractRecord(
            ocid=source_ocid,
            award_ocid=source_ocid,
            tender_ocid=tender_ocid,
            title=title,
            status=status,
            source_url=MTENDER_CONTRACTS_URL,
        )
    record.award_ocid = source_ocid
    record.tender_ocid = tender_ocid
    record.title = title
    record.status = status
    record.signed_at = source_modified_at or datetime.now(timezone.utc)
    record.amount = float(amount) if amount is not None else None
    record.currency = currency
    record.supplier_name = supplier_name
    record.buyer_name = buyer_name
    record.buyer_sector = buyer_sector
    record.raion = raion
    record.source_url = MTENDER_CONTRACTS_URL
    record.source_collection = "contracts"
    record.source_modified_at = source_modified_at
    record.tags = tags
    record.raw_payload = item
    record.synced_at = datetime.now(timezone.utc)
    session.add(record)
    return record


def _upsert_budget(session: Session, item: dict[str, Any]) -> ProcurementBudgetRecord | None:
    source_id = clean_text(item.get("id") or "")
    entity_id = clean_text(item.get("entityId") or source_id)
    if not source_id or not entity_id:
        return None

    title = clean_text(item.get("title") or source_id)
    description = clean_text(item.get("description") or "")
    status = clean_text(item.get("budgetStatus") or "") or None
    amount = item.get("amount")
    currency = clean_text(item.get("currency") or "MDL") or "MDL"
    raion = clean_text(item.get("buyerRegion") or "") or None
    buyer_name = clean_text(item.get("buyerName") or "") or None
    buyer_sector = infer_sector(title, description, buyer_name, raion)
    planning_from = parse_datetime(item.get("periodPlanningFrom"))
    planning_to = parse_datetime(item.get("periodPlanningTo"))
    source_modified_at = parse_datetime(item.get("modifiedDate"))

    record = session.scalar(select(ProcurementBudgetRecord).where(ProcurementBudgetRecord.source_id == source_id))
    if record is None:
        record = ProcurementBudgetRecord(source_id=source_id, entity_id=entity_id, title=title, source_url=MTENDER_BUDGETS_URL)

    record.entity_id = entity_id
    record.title = title
    record.description = description or None
    record.status = status
    record.amount = float(amount) if amount is not None else None
    record.currency = currency
    record.raion = raion
    record.buyer_name = buyer_name
    record.buyer_sector = buyer_sector
    record.planning_from = planning_from
    record.planning_to = planning_to
    record.source_url = MTENDER_BUDGETS_URL
    record.source_collection = "budgets"
    record.source_modified_at = source_modified_at
    record.raw_payload = item
    record.synced_at = datetime.now(timezone.utc)
    session.add(record)
    return record


def _upsert_plan(session: Session, item: dict[str, Any]) -> ProcurementPlanRecord | None:
    ocid = clean_text(item.get("id") or "")
    entity_id = clean_text(item.get("entityId") or ocid)
    if not ocid or not entity_id:
        return None

    title = clean_text(item.get("title") or ocid)
    description = clean_text(item.get("description") or "")
    tags = [clean_text(tag) for tag in (item.get("tags") or []) if clean_text(tag)]
    status = "planning" if "planning" in {tag.lower() for tag in tags} else clean_text(item.get("procedureStatus") or "published") or "published"
    amount = item.get("amount")
    currency = clean_text(item.get("currency") or "MDL") or "MDL"
    raion = clean_text(item.get("buyerRegion") or "") or None
    buyer_name = clean_text(item.get("buyerName") or "") or None
    buyer_sector = infer_sector(title, description, buyer_name, raion)
    source_modified_at = parse_datetime(item.get("modifiedDate"))
    pin = parse_bool(item.get("pin"))

    record = session.scalar(select(ProcurementPlanRecord).where(ProcurementPlanRecord.ocid == ocid))
    if record is None:
        record = ProcurementPlanRecord(ocid=ocid, entity_id=entity_id, title=title, status=status, source_url=MTENDER_PLANS_URL)

    record.entity_id = entity_id
    record.title = title
    record.status = status
    record.raion = raion
    record.buyer_name = buyer_name
    record.buyer_sector = buyer_sector
    record.amount = float(amount) if amount is not None else None
    record.currency = currency
    record.pin = pin
    record.tags = tags
    record.related_tender_ocids = unique_list([entity_id])
    record.source_url = MTENDER_PLANS_URL
    record.source_collection = "plans"
    record.source_modified_at = source_modified_at
    record.raw_payload = item
    record.synced_at = datetime.now(timezone.utc)
    session.add(record)
    return record


def sync_mtender_database(
    *,
    session: Session | None = None,
    tender_pages: int = 2,
    tender_page_size: int = 10,
    contract_pages: int = 1,
    contract_page_size: int = 25,
    budget_pages: int = 1,
    budget_page_size: int = 25,
    plan_pages: int = 1,
    plan_page_size: int = 25,
) -> dict[str, int]:
    ensure_schema()
    counts = {"tenders": 0, "awards": 0, "contracts": 0, "budgets": 0, "plans": 0, "links": 0}

    with _session_scope(session) as db:
        for page in range(1, tender_pages + 1):
            payload = fetch_mtender_collection("tenders", page=page, page_size=tender_page_size)
            items = payload.get("data") or []
            if not items:
                break
            for summary in items:
                ocid = clean_text(summary.get("entityId") or summary.get("id") or "")
                if not ocid:
                    continue
                detail_payload = fetch_mtender_detail(ocid)
                if _upsert_tender(db, summary, detail_payload) is not None:
                    counts["tenders"] += 1

        for page in range(1, contract_pages + 1):
            payload = fetch_mtender_collection("contracts", page=page, page_size=contract_page_size)
            items = payload.get("data") or []
            if not items:
                break
            for item in items:
                if _upsert_award_or_contract_record(db, item, kind="award") is not None:
                    counts["awards"] += 1
                if _upsert_award_or_contract_record(db, item, kind="contract") is not None:
                    counts["contracts"] += 1

        for page in range(1, budget_pages + 1):
            payload = fetch_mtender_collection("budgets", page=page, page_size=budget_page_size)
            items = payload.get("data") or []
            if not items:
                break
            for item in items:
                if _upsert_budget(db, item) is not None:
                    counts["budgets"] += 1

        for page in range(1, plan_pages + 1):
            payload = fetch_mtender_collection("plans", page=page, page_size=plan_page_size)
            items = payload.get("data") or []
            if not items:
                break
            for item in items:
                if _upsert_plan(db, item) is not None:
                    counts["plans"] += 1

        link_summary = rebuild_cross_references(db)
        counts["links"] = link_summary["links"]
        db.commit()

    return counts


def sync_mtender_tender(ocid: str, *, session: Session | None = None) -> ProcurementTenderRecord | None:
    ensure_schema()
    with _session_scope(session) as db:
        detail_payload = fetch_mtender_detail(ocid)
        release = _choose_release(detail_payload)
        summary = {
            "entityId": ocid,
            "id": ocid,
            "title": (release.get("tender") or {}).get("title"),
            "description": (release.get("tender") or {}).get("description"),
            "buyerRegion": _first_party_value(release, "raion"),
            "procedureType": (release.get("tender") or {}).get("procurementMethodDetails"),
            "amount": ((release.get("tender") or {}).get("value") or {}).get("amount"),
            "currency": ((release.get("tender") or {}).get("value") or {}).get("currency"),
            "modifiedDate": release.get("date"),
            "buyerName": ((release.get("tender") or {}).get("procuringEntity") or {}).get("name"),
            "procedureStatus": (release.get("tender") or {}).get("status"),
        }
        record = _upsert_tender(db, summary, detail_payload)
        rebuild_cross_references(db)
        db.commit()
        return record


def _query_tenders(session: Session, *, raion: str | None = None, status: str | None = None, query: str | None = None) -> list[ProcurementTenderRecord]:
    stmt = select(ProcurementTenderRecord)
    if raion:
        stmt = stmt.where(func.lower(ProcurementTenderRecord.raion) == raion.lower())
    if status:
        stmt = stmt.where(func.lower(ProcurementTenderRecord.status) == status.lower())
    if query:
        needle = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                ProcurementTenderRecord.title.ilike(needle),
                ProcurementTenderRecord.description.ilike(needle),
                ProcurementTenderRecord.buyer_name.ilike(needle),
                ProcurementTenderRecord.raion.ilike(needle),
            )
        )
    return session.scalars(stmt.order_by(ProcurementTenderRecord.date_published.desc(), ProcurementTenderRecord.ocid.desc())).all()


def _query_awards(session: Session, *, raion: str | None = None) -> list[ProcurementAwardRecord]:
    stmt = select(ProcurementAwardRecord)
    if raion:
        stmt = stmt.where(func.lower(ProcurementAwardRecord.raion) == raion.lower())
    return session.scalars(stmt.order_by(ProcurementAwardRecord.source_modified_at.desc().nullslast(), ProcurementAwardRecord.ocid.desc())).all()


def _query_contracts(session: Session, *, raion: str | None = None) -> list[ProcurementContractRecord]:
    stmt = select(ProcurementContractRecord)
    if raion:
        stmt = stmt.where(func.lower(ProcurementContractRecord.raion) == raion.lower())
    return session.scalars(stmt.order_by(ProcurementContractRecord.source_modified_at.desc().nullslast(), ProcurementContractRecord.ocid.desc())).all()


def _query_budgets(session: Session, *, raion: str | None = None) -> list[ProcurementBudgetRecord]:
    stmt = select(ProcurementBudgetRecord)
    if raion:
        stmt = stmt.where(func.lower(ProcurementBudgetRecord.raion) == raion.lower())
    return session.scalars(stmt.order_by(ProcurementBudgetRecord.source_modified_at.desc().nullslast(), ProcurementBudgetRecord.source_id.desc())).all()


def _query_plans(session: Session, *, raion: str | None = None) -> list[ProcurementPlanRecord]:
    stmt = select(ProcurementPlanRecord)
    if raion:
        stmt = stmt.where(func.lower(ProcurementPlanRecord.raion) == raion.lower())
    return session.scalars(stmt.order_by(ProcurementPlanRecord.source_modified_at.desc().nullslast(), ProcurementPlanRecord.ocid.desc())).all()


def _tender_to_schema(record: ProcurementTenderRecord) -> ProcurementTender:
    location = None
    if record.raion or record.city:
        location = Location(raion=record.raion or "Unknown", city=record.city)
    return ProcurementTender(
        ocid=record.ocid,
        title=record.title,
        description=record.description,
        status=record.status,
        date_published=record.date_published,
        value=OCDSAmount(amount=record.amount, currency=record.currency) if record.amount is not None else None,
        location=location,
        buyer=BuyerReference(id=record.buyer_id, name=record.buyer_name, sector=record.buyer_sector),
        cross_references=dict(record.cross_references or {}),
    )


def _award_to_schema(record: ProcurementAwardRecord) -> ProcurementAward:
    return ProcurementAward(
        ocid=record.ocid,
        tender_ocid=record.tender_ocid,
        title=record.title,
        status=record.status,
        value=OCDSAmount(amount=record.amount, currency=record.currency) if record.amount is not None else None,
        supplier_name=record.supplier_name,
        raion=record.raion,
    )


def _contract_to_schema(record: ProcurementContractRecord) -> ProcurementContract:
    return ProcurementContract(
        ocid=record.ocid,
        award_ocid=record.award_ocid,
        title=record.title,
        status=record.status,
        signed_at=record.signed_at or datetime.now(timezone.utc),
        value=OCDSAmount(amount=record.amount, currency=record.currency) if record.amount is not None else None,
        supplier_name=record.supplier_name,
        raion=record.raion,
    )


def _budget_to_schema(record: ProcurementBudgetRecord) -> ProcurementBudget:
    return ProcurementBudget(
        code=record.source_id,
        name=record.title,
        amount=OCDSAmount(amount=record.amount or 0.0, currency=record.currency),
        raion=record.raion,
    )


def _plan_to_schema(record: ProcurementPlanRecord) -> ProcurementPlan:
    return ProcurementPlan(
        ocid=record.ocid,
        title=record.title,
        status=record.status,
        raion=record.raion,
        related_tender_ocids=list(record.related_tender_ocids or []),
    )


def list_tenders(*, raion: str | None = None, status: str | None = None, query: str | None = None, sync_if_empty: bool = True, session: Session | None = None) -> list[ProcurementTender]:
    ensure_schema()
    with _session_scope(session) as db:
        if sync_if_empty and not db.scalar(select(func.count()).select_from(ProcurementTenderRecord)):
            try:
                sync_mtender_database(session=db)
            except Exception:
                logger.exception("MTender sync failed")
        rows = _query_tenders(db, raion=raion, status=status, query=query)
        return [_tender_to_schema(record) for record in rows]


def get_tender(ocid: str, *, sync_if_missing: bool = True, session: Session | None = None) -> ProcurementTender | None:
    ensure_schema()
    with _session_scope(session) as db:
        record = db.scalar(select(ProcurementTenderRecord).where(ProcurementTenderRecord.ocid == ocid))
        if record is None and sync_if_missing:
            try:
                sync_mtender_tender(ocid, session=db)
            except Exception:
                logger.exception("MTender tender sync failed for %s", ocid)
            record = db.scalar(select(ProcurementTenderRecord).where(ProcurementTenderRecord.ocid == ocid))
        return _tender_to_schema(record) if record else None


def list_awards(*, raion: str | None = None, sync_if_empty: bool = True, session: Session | None = None) -> list[ProcurementAward]:
    ensure_schema()
    with _session_scope(session) as db:
        if sync_if_empty and not db.scalar(select(func.count()).select_from(ProcurementAwardRecord)):
            try:
                sync_mtender_database(session=db)
            except Exception:
                logger.exception("MTender award sync failed")
        return [_award_to_schema(record) for record in _query_awards(db, raion=raion)]


def list_contracts(*, raion: str | None = None, sync_if_empty: bool = True, session: Session | None = None) -> list[ProcurementContract]:
    ensure_schema()
    with _session_scope(session) as db:
        if sync_if_empty and not db.scalar(select(func.count()).select_from(ProcurementContractRecord)):
            try:
                sync_mtender_database(session=db)
            except Exception:
                logger.exception("MTender contract sync failed")
        return [_contract_to_schema(record) for record in _query_contracts(db, raion=raion)]


def list_budgets(*, raion: str | None = None, sync_if_empty: bool = True, session: Session | None = None) -> list[ProcurementBudget]:
    ensure_schema()
    with _session_scope(session) as db:
        if sync_if_empty and not db.scalar(select(func.count()).select_from(ProcurementBudgetRecord)):
            try:
                sync_mtender_database(session=db)
            except Exception:
                logger.exception("MTender budget sync failed")
        return [_budget_to_schema(record) for record in _query_budgets(db, raion=raion)]


def list_plans(*, raion: str | None = None, sync_if_empty: bool = True, session: Session | None = None) -> list[ProcurementPlan]:
    ensure_schema()
    with _session_scope(session) as db:
        if sync_if_empty and not db.scalar(select(func.count()).select_from(ProcurementPlanRecord)):
            try:
                sync_mtender_database(session=db)
            except Exception:
                logger.exception("MTender plan sync failed")
        return [_plan_to_schema(record) for record in _query_plans(db, raion=raion)]


def get_statistics(*, raion: str | None = None, sync_if_empty: bool = True, session: Session | None = None) -> ProcurementStatistics:
    ensure_schema()
    with _session_scope(session) as db:
        if sync_if_empty and not db.scalar(select(func.count()).select_from(ProcurementTenderRecord)):
            try:
                sync_mtender_database(session=db)
            except Exception:
                logger.exception("MTender statistics sync failed")

        tender_stmt = select(ProcurementTenderRecord)
        if raion:
            tender_stmt = tender_stmt.where(func.lower(ProcurementTenderRecord.raion) == raion.lower())

        tenders = db.scalars(tender_stmt).all()
        awards = db.scalar(select(func.count()).select_from(ProcurementAwardRecord)) or 0
        contracts = db.scalar(select(func.count()).select_from(ProcurementContractRecord)) or 0
        budgets = db.scalars(select(ProcurementBudgetRecord)).all()

        by_raion_rows = db.execute(
            select(
                ProcurementTenderRecord.raion,
                func.sum(ProcurementTenderRecord.amount),
            )
            .where(ProcurementTenderRecord.raion.isnot(None))
            .group_by(ProcurementTenderRecord.raion)
            .order_by(func.sum(ProcurementTenderRecord.amount).desc())
        ).all()
        by_raion = {
            raion_name: OCDSAmount(amount=float(total or 0.0), currency="MDL")
            for raion_name, total in by_raion_rows
            if raion_name
        }
        if raion:
            by_raion = {key: value for key, value in by_raion.items() if key.lower() == raion.lower()}

        sector_rows = db.execute(
            select(
                ProcurementTenderRecord.buyer_sector,
                func.count(ProcurementTenderRecord.id),
            )
            .where(ProcurementTenderRecord.buyer_sector.isnot(None))
            .group_by(ProcurementTenderRecord.buyer_sector)
            .order_by(func.count(ProcurementTenderRecord.id).desc())
        ).all()
        top_sectors = [sector for sector, _ in sector_rows if sector][:3]
        if not top_sectors:
            top_sectors = ["General"]

        return ProcurementStatistics(
            total_tenders=len(tenders),
            total_awards=awards,
            total_contracts=contracts,
            total_budget=OCDSAmount(
                amount=float(sum((budget.amount or 0.0) for budget in budgets)),
                currency="MDL",
            ),
            by_raion=by_raion,
            top_sectors=top_sectors,
        )
