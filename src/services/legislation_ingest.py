from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.api.v1.schemas import LegislationArticle, LegislationEdition
from src.db import session as db_session
from src.db.models import LegislationArticleRecord, LegislationEditionRecord
from src.services.ingest_utils import clean_text, json_safe, parse_datetime

logger = logging.getLogger(__name__)

MONITORUL_URL = "https://monitorul.gov.md/"
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


def _edition_key_from_href(href: str, text: str) -> str:
    candidate = clean_text(href.rstrip("/").split("/")[-1]) or clean_text(text)
    candidate = re.sub(r"[^0-9A-Za-z._-]+", "-", candidate).strip("-")
    return candidate[:255] or "edition"


def fetch_monitorul_homepage() -> dict[str, Any]:
    with _client() as client:
        response = client.get(MONITORUL_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        editions: list[dict[str, Any]] = []
        seen: set[str] = set()
        for anchor in soup.select("a[href]"):
            href = anchor.get("href") or ""
            text = clean_text(anchor.get_text(" ", strip=True))
            if not text and not href:
                continue
            if ".pdf" not in href.lower() and "monitorul" not in href.lower() and "edition" not in text.lower():
                continue
            edition_key = _edition_key_from_href(href, text)
            if edition_key in seen:
                continue
            seen.add(edition_key)
            editions.append(
                {
                    "edition_key": edition_key,
                    "edition_number": text or edition_key,
                    "title": text or edition_key,
                    "published_at": None,
                    "pdf_url": href if href.startswith("http") else urljoin(MONITORUL_URL, href),
                    "source_url": href if href.startswith("http") else MONITORUL_URL,
                    "summary": text,
                }
            )
        return {"editions": editions, "raw_text": clean_text(soup.get_text(" ", strip=True))}


def _edition_to_schema(record: LegislationEditionRecord) -> LegislationEdition:
    return LegislationEdition(
        edition_key=record.edition_key,
        edition_number=record.edition_number,
        title=record.title,
        published_at=record.published_at,
        pdf_url=record.pdf_url,
        source_url=record.source_url,
        summary=record.summary,
    )


def _article_to_schema(record: LegislationArticleRecord) -> LegislationArticle:
    return LegislationArticle(
        article_key=record.article_key,
        edition_key=record.edition_key,
        article_number=record.article_number,
        title=record.title,
        content_snippet=record.content_snippet,
        source_url=record.source_url,
    )


def sync_legislation_database(*, session: Session | None = None, limit: int = 20) -> dict[str, int]:
    ensure_schema()
    with _session_scope(session) as db:
        payload = fetch_monitorul_homepage()
        editions = payload.get("editions") or []
        counts = {"editions": 0, "articles": 0}

        for index, edition in enumerate(editions[:limit], start=1):
            edition_key = clean_text(edition.get("edition_key") or f"edition-{index}")
            record = db.scalar(select(LegislationEditionRecord).where(LegislationEditionRecord.edition_key == edition_key))
            if record is None:
                record = LegislationEditionRecord(
                    edition_key=edition_key,
                    edition_number=clean_text(edition.get("edition_number") or edition_key),
                    title=clean_text(edition.get("title") or edition_key),
                    source_url=clean_text(edition.get("source_url") or MONITORUL_URL),
                )
                counts["editions"] += 1

            record.edition_number = clean_text(edition.get("edition_number") or edition_key)
            record.title = clean_text(edition.get("title") or edition_key)
            record.published_at = parse_datetime(edition.get("published_at"))
            record.pdf_url = clean_text(edition.get("pdf_url") or "") or None
            record.source_url = clean_text(edition.get("source_url") or MONITORUL_URL)
            record.summary = clean_text(edition.get("summary") or "")
            record.raw_payload = json_safe(edition)
            record.synced_at = datetime.now(timezone.utc)
            db.add(record)

            article_key = f"{edition_key}:summary"
            article = db.scalar(select(LegislationArticleRecord).where(LegislationArticleRecord.article_key == article_key))
            if article is None:
                article = LegislationArticleRecord(
                    article_key=article_key,
                    edition_key=edition_key,
                    article_number="summary",
                    title=record.title,
                    content_snippet=record.summary or record.title,
                    source_url=record.pdf_url or record.source_url,
                )
                counts["articles"] += 1
            article.edition_key = edition_key
            article.article_number = "summary"
            article.title = record.title
            article.content_snippet = record.summary or record.title
            article.source_url = record.pdf_url or record.source_url
            article.raw_payload = json_safe(edition)
            article.synced_at = datetime.now(timezone.utc)
            db.add(article)

        db.commit()
        return counts


def _query_editions(db: Session, query: str | None = None) -> list[LegislationEditionRecord]:
    stmt = select(LegislationEditionRecord)
    if query:
        terms = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                LegislationEditionRecord.edition_key.ilike(terms),
                LegislationEditionRecord.edition_number.ilike(terms),
                LegislationEditionRecord.title.ilike(terms),
                LegislationEditionRecord.summary.ilike(terms),
            )
        )
    stmt = stmt.order_by(LegislationEditionRecord.updated_at.desc(), LegislationEditionRecord.published_at.desc().nullslast())
    return list(db.scalars(stmt).all())


def _query_articles(db: Session, query: str | None = None) -> list[LegislationArticleRecord]:
    stmt = select(LegislationArticleRecord)
    if query:
        terms = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                LegislationArticleRecord.article_key.ilike(terms),
                LegislationArticleRecord.title.ilike(terms),
                LegislationArticleRecord.content_snippet.ilike(terms),
                LegislationArticleRecord.article_number.ilike(terms),
            )
        )
    stmt = stmt.order_by(LegislationArticleRecord.updated_at.desc())
    return list(db.scalars(stmt).all())


def list_editions(*, query: str | None = None, sync_if_empty: bool = True, session: Session | None = None) -> list[LegislationEdition]:
    ensure_schema()
    with _session_scope(session) as db:
        if sync_if_empty and not db.scalar(select(func.count()).select_from(LegislationEditionRecord)):
            try:
                sync_legislation_database(session=db)
            except Exception:
                logger.exception("Legislation sync failed")
        return [_edition_to_schema(record) for record in _query_editions(db, query=query)]


def list_articles(*, query: str | None = None, sync_if_empty: bool = True, session: Session | None = None) -> list[LegislationArticle]:
    ensure_schema()
    with _session_scope(session) as db:
        if sync_if_empty and not db.scalar(select(func.count()).select_from(LegislationArticleRecord)):
            try:
                sync_legislation_database(session=db)
            except Exception:
                logger.exception("Legislation article sync failed")
        return [_article_to_schema(record) for record in _query_articles(db, query=query)]


def get_edition(edition_key: str, *, sync_if_missing: bool = True, session: Session | None = None) -> LegislationEdition | None:
    ensure_schema()
    with _session_scope(session) as db:
        record = db.scalar(select(LegislationEditionRecord).where(LegislationEditionRecord.edition_key == edition_key))
        if record is None and sync_if_missing:
            try:
                sync_legislation_database(session=db)
            except Exception:
                logger.exception("Legislation sync failed for %s", edition_key)
            record = db.scalar(select(LegislationEditionRecord).where(LegislationEditionRecord.edition_key == edition_key))
        return _edition_to_schema(record) if record else None
