from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.api.v1.schemas import EUFundingStatistics, EUProject, Location, OCDSAmount
from src.db import session as db_session
from src.db.models import EUProjectRecord, ProcurementTenderRecord
from src.services.cross_reference import rebuild_cross_references
from src.services.ingest_utils import clean_text, date_to_datetime, infer_sector, json_safe, parse_ddmmyyyy, parse_datetime, unique_list

logger = logging.getLogger(__name__)

EU_PROJECTS_URL = "https://eu4moldova.eu/en/projects/"
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


def _listing_url(page: int) -> str:
    if page <= 1:
        return EU_PROJECTS_URL
    return f"{EU_PROJECTS_URL}?filter=ongoing&country_view%5B0%5D=1&country_view%5B1%5D=4&pageno={page}"


def _extract_project_id(href: str) -> str | None:
    parsed = urlparse(href)
    project_id = parse_qs(parsed.query).get("id", [None])[0]
    return clean_text(project_id) or None


def _extract_listing_projects(html: str, page_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for anchor in soup.select('a[href*="/en/projects/eu-project-page/"]'):
        text = clean_text(anchor.get_text(" ", strip=True))
        if not text or text.upper() == "READ MORE":
            continue
        href = urljoin(page_url, anchor.get("href"))
        project_id = _extract_project_id(href)
        if not project_id or project_id in seen:
            continue
        seen.add(project_id)
        match = re.search(r"Start Date\s+(\d{2}\.\d{2}\.\d{4})\s+End Date\s+(\d{2}\.\d{2}\.\d{4})", text)
        start_date = parse_ddmmyyyy(match.group(1)) if match else None
        end_date = parse_ddmmyyyy(match.group(2)) if match else None
        title = text.split(" Start Date ", 1)[0].strip()
        rows.append(
            {
                "project_id": project_id,
                "title": title,
                "start_date": start_date,
                "end_date": end_date,
                "source_url": href,
                "listing_text": text,
            }
        )
    return rows


def fetch_eu_projects_page(page: int = 1) -> list[dict[str, Any]]:
    with _client() as client:
        url = _listing_url(page)
        response = client.get(url)
        response.raise_for_status()
        return _extract_listing_projects(response.text, url)


def _project_section_text(container: BeautifulSoup, label: str) -> str | None:
    heading = container.find(lambda tag: tag.name == "h5" and label in tag.get_text(" ", strip=True))
    if heading is None:
        return None
    parts: list[str] = []
    for sibling in heading.next_siblings:
        if getattr(sibling, "name", None) == "h5":
            break
        if getattr(sibling, "get_text", None):
            text = clean_text(sibling.get_text(" ", strip=True))
            if text:
                parts.append(text)
    value = clean_text(" ".join(parts))
    return value or None


def _extract_labeled_value(text: str, label: str, stop_labels: list[str]) -> str | None:
    stop_pattern = "|".join(re.escape(f"{candidate}:") for candidate in stop_labels)
    if stop_pattern:
        pattern = rf"{re.escape(label)}:\s*(.*?)(?=(?:{stop_pattern}|DOWNLOAD PDF|$))"
    else:
        pattern = rf"{re.escape(label)}:\s*(.*?)(?=(?:DOWNLOAD PDF|$))"
    match = re.search(pattern, text, flags=re.S)
    if not match:
        return None
    value = clean_text(match.group(1))
    return value or None


def _parse_detail_page(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    description_container = soup.find(lambda tag: tag.name == "h5" and "Project Description" in tag.get_text(" ", strip=True))
    details_container = soup.find(lambda tag: tag.name == "h5" and "PROJECT DETAILS" in tag.get_text(" ", strip=True))

    description_parent = description_container.parent if description_container else None
    details_parent = details_container.parent if details_container else None

    title = ""
    description = ""
    objective = ""
    results = ""
    if description_parent is not None:
        title_tag = description_parent.find("h3")
        if title_tag is not None:
            title = clean_text(title_tag.get_text(" ", strip=True))
        description = _project_section_text(description_parent, "Project Description") or ""
        objective = _project_section_text(description_parent, "Specific Objective") or ""
        results = _project_section_text(description_parent, "Expected Results") or ""

    detail_text = clean_text(details_parent.get_text(" ", strip=True)) if details_parent is not None else ""
    region_label = None
    if detail_text:
        region_match = re.search(r"PROJECT DETAILS\s*(.*?)\s*Priority Area:", detail_text, flags=re.S)
        if region_match:
            region_label = clean_text(region_match.group(1)) or None

    priority_area = _extract_labeled_value(detail_text, "Priority Area", ["Subsector", "Topic", "EaP Countries", "Project Status", "Start Date", "End Date", "Website", "Social Media Links", "EU Project Number"])
    subsector = _extract_labeled_value(detail_text, "Subsector", ["Topic", "EaP Countries", "Project Status", "Start Date", "End Date", "Website", "Social Media Links", "EU Project Number"])
    topic = _extract_labeled_value(detail_text, "Topic", ["EaP Countries", "Project Status", "Start Date", "End Date", "Website", "Social Media Links", "EU Project Number"])
    countries_text = _extract_labeled_value(detail_text, "EaP Countries", ["Project Status", "Start Date", "End Date", "Website", "Social Media Links", "EU Project Number"]) or ""
    status = (_extract_labeled_value(detail_text, "Project Status", ["Start Date", "End Date", "Website", "Social Media Links", "EU Project Number"]) or "ongoing").lower()
    start_date = parse_ddmmyyyy(_extract_labeled_value(detail_text, "Start Date", ["End Date", "Website", "Social Media Links", "EU Project Number"]))
    end_date = parse_ddmmyyyy(_extract_labeled_value(detail_text, "End Date", ["Website", "Social Media Links", "EU Project Number"]))
    project_number = _extract_labeled_value(detail_text, "EU Project Number", []) or None

    social_links: list[str] = []
    website_url = None
    if details_parent is not None:
        for anchor in details_parent.find_all("a", href=True):
            href = anchor["href"].strip()
            if "facebook.com" in href.lower() or "linkedin.com" in href.lower() or "x.com" in href.lower():
                social_links.append(href)
            elif href.startswith("http") and website_url is None and "eu4moldova.eu" not in href.lower():
                website_url = href

    countries = [clean_text(part) for part in countries_text.split(",") if clean_text(part)]
    sector = infer_sector(title, description, objective, results, priority_area, subsector, topic)

    return {
        "title": title,
        "description": description or objective or results or title,
        "priority_area": priority_area,
        "subsector": subsector,
        "topic": topic,
        "countries": countries,
        "status": status,
        "start_date": start_date,
        "end_date": end_date,
        "project_number": project_number,
        "website_url": website_url,
        "social_links": unique_list(social_links),
        "region_label": region_label,
        "sector": sector,
        "raw_text": detail_text,
        "specific_objective": objective,
        "expected_results": results,
    }


def fetch_eu_project_detail(url: str) -> dict[str, Any]:
    with _client() as client:
        response = client.get(url)
        response.raise_for_status()
        return _parse_detail_page(response.text)


def _upsert_project(session: Session, listing_item: dict[str, Any], detail_item: dict[str, Any]) -> EUProjectRecord | None:
    project_id = clean_text(listing_item.get("project_id") or "")
    if not project_id:
        return None

    title = clean_text(detail_item.get("title") or listing_item.get("title") or project_id)
    description = clean_text(detail_item.get("description") or title)
    sector = clean_text(detail_item.get("sector") or infer_sector(title, description, detail_item.get("priority_area"), detail_item.get("subsector"), detail_item.get("topic"))) or "General"
    status = clean_text(detail_item.get("status") or "ongoing") or "ongoing"
    start_date = detail_item.get("start_date") or listing_item.get("start_date")
    end_date = detail_item.get("end_date") or listing_item.get("end_date")
    source_url = clean_text(listing_item.get("source_url") or f"{EU_PROJECTS_URL.rstrip('/')}/eu-project-page/?id={project_id}")

    record = session.scalar(select(EUProjectRecord).where(EUProjectRecord.project_id == project_id))
    if record is None:
        record = EUProjectRecord(project_id=project_id, title=title, description=description, status=status, sector=sector, source_url=source_url)

    record.title = title
    record.description = description
    record.status = status
    record.sector = sector
    record.raw_sector = detail_item.get("topic") or detail_item.get("subsector") or detail_item.get("priority_area")
    record.priority_area = detail_item.get("priority_area")
    record.subsector = detail_item.get("subsector")
    record.topic = detail_item.get("topic")
    record.countries = list(detail_item.get("countries") or [])
    record.funding_amount = None
    record.currency = "EUR"
    record.start_date = start_date or listing_item.get("start_date") or datetime.now(timezone.utc)
    record.end_date = end_date or listing_item.get("end_date")
    record.beneficiary = None
    record.raion = None
    record.region_label = detail_item.get("region_label")
    record.project_number = detail_item.get("project_number")
    record.website_url = detail_item.get("website_url")
    record.social_links = list(detail_item.get("social_links") or [])
    record.linked_procurement_ocids = list(record.linked_procurement_ocids or [])
    record.source_url = source_url
    record.source_collection = "eu-projects"
    record.source_modified_at = None
    record.raw_payload = {
        "listing": json_safe(listing_item),
        "detail": json_safe(detail_item),
        "detail_text": detail_item.get("raw_text"),
        "specific_objective": detail_item.get("specific_objective"),
        "expected_results": detail_item.get("expected_results"),
    }
    record.synced_at = datetime.now(timezone.utc)
    session.add(record)
    return record


def sync_eu_funds_database(*, session: Session | None = None, max_pages: int = 1) -> dict[str, int]:
    ensure_schema()
    counts = {"projects": 0, "links": 0}

    with _session_scope(session) as db:
        for page in range(1, max_pages + 1):
            listing_items = fetch_eu_projects_page(page=page)
            if not listing_items:
                break
            for listing_item in listing_items:
                detail_payload = fetch_eu_project_detail(listing_item["source_url"])
                if _upsert_project(db, listing_item, detail_payload) is not None:
                    counts["projects"] += 1

        link_summary = rebuild_cross_references(db)
        counts["links"] = link_summary["links"]
        db.commit()

    return counts


def _query_projects(session: Session, *, status: str | None = None, sector: str | None = None, raion: str | None = None) -> list[EUProjectRecord]:
    stmt = select(EUProjectRecord)
    if status:
        stmt = stmt.where(func.lower(EUProjectRecord.status) == status.lower())
    if sector:
        stmt = stmt.where(func.lower(EUProjectRecord.sector) == sector.lower())
    if raion:
        stmt = stmt.where(func.lower(EUProjectRecord.raion) == raion.lower())
    return session.scalars(stmt.order_by(EUProjectRecord.start_date.desc().nullslast(), EUProjectRecord.project_id.desc())).all()


def _project_to_schema(record: EUProjectRecord) -> EUProject:
    location = None
    if record.raion:
        location = Location(raion=record.raion, city=None)
    return EUProject(
        id=record.project_id,
        title=record.title,
        description=record.description,
        status=record.status,
        sector=record.sector,
        funding_amount=OCDSAmount(amount=record.funding_amount, currency=record.currency) if record.funding_amount is not None else None,
        start_date=record.start_date,
        end_date=record.end_date,
        beneficiary=record.beneficiary,
        location=location,
        linked_procurement_ocids=list(record.linked_procurement_ocids or []),
    )


def list_projects(*, status: str | None = None, sector: str | None = None, raion: str | None = None, sync_if_empty: bool = True, session: Session | None = None) -> list[EUProject]:
    ensure_schema()
    with _session_scope(session) as db:
        if sync_if_empty and not db.scalar(select(func.count()).select_from(EUProjectRecord)):
            try:
                sync_eu_funds_database(session=db)
            except Exception:
                logger.exception("EU funding sync failed")
        return [_project_to_schema(record) for record in _query_projects(db, status=status, sector=sector, raion=raion)]


def get_project(project_id: str, *, sync_if_missing: bool = True, session: Session | None = None) -> EUProject | None:
    ensure_schema()
    with _session_scope(session) as db:
        record = db.scalar(select(EUProjectRecord).where(EUProjectRecord.project_id == project_id))
        if record is None and sync_if_missing:
            try:
                sync_eu_funds_database(session=db)
            except Exception:
                logger.exception("EU project sync failed for %s", project_id)
            record = db.scalar(select(EUProjectRecord).where(EUProjectRecord.project_id == project_id))
        return _project_to_schema(record) if record else None


def get_statistics(*, sync_if_empty: bool = True, session: Session | None = None) -> EUFundingStatistics:
    ensure_schema()
    with _session_scope(session) as db:
        if sync_if_empty and not db.scalar(select(func.count()).select_from(EUProjectRecord)):
            try:
                sync_eu_funds_database(session=db)
            except Exception:
                logger.exception("EU funding statistics sync failed")

        projects = db.scalars(select(EUProjectRecord)).all()
        currency = next((project.currency for project in projects if project.currency), "EUR")
        total_funding = float(sum((project.funding_amount or 0.0) for project in projects))

        sector_rows = db.execute(
            select(
                EUProjectRecord.sector,
                func.sum(EUProjectRecord.funding_amount),
            )
            .group_by(EUProjectRecord.sector)
            .order_by(func.sum(EUProjectRecord.funding_amount).desc())
        ).all()
        by_sector = {
            sector: OCDSAmount(amount=float(total or 0.0), currency=currency)
            for sector, total in sector_rows
            if sector
        }

        raion_rows = db.execute(
            select(
                EUProjectRecord.raion,
                func.sum(EUProjectRecord.funding_amount),
            )
            .where(EUProjectRecord.raion.isnot(None))
            .group_by(EUProjectRecord.raion)
            .order_by(func.sum(EUProjectRecord.funding_amount).desc())
        ).all()
        by_raion = {
            raion: OCDSAmount(amount=float(total or 0.0), currency=currency)
            for raion, total in raion_rows
            if raion
        }

        return EUFundingStatistics(
            total_projects=len(projects),
            total_funding=OCDSAmount(amount=total_funding, currency=currency),
            by_sector=by_sector,
            by_raion=by_raion,
        )
