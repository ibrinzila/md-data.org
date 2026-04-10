from __future__ import annotations

from collections.abc import Iterable
from contextlib import contextmanager

from sqlalchemy.orm import Session

from src.api.v1.schemas import SearchResult
from src.db import session as db_session
from src.services.ckan_ingest import list_datasets
from src.services.eu_funds_ingest import list_projects
from src.services.geospatial_ingest import list_layers
from src.services.legislation_ingest import list_articles, list_editions
from src.services.mtender_ingest import list_tenders
from src.services.registry_ingest import list_entities
from src.services.normalizer import normalize_query

STATIC_CATALOG = [
    SearchResult(
        title="BNM exchange rates",
        description="Official exchange-rate endpoint backed by BNM XML.",
        url="/v1/finance/exchange-rates",
        source="BNM",
    ),
    SearchResult(
        title="MTender tenders",
        description="Public procurement feed linked to the MTender portal.",
        url="/v1/procurement/tenders",
        source="MTender",
    ),
    SearchResult(
        title="EU funding projects",
        description="EU4Moldova and Growth Plan project index.",
        url="/v1/eu-funds/projects",
        source="EU Funds",
    ),
    SearchResult(
        title="Open datasets",
        description="CKAN datasets from the Government Open Data Portal.",
        url="/v1/datasets",
        source="CKAN",
    ),
    SearchResult(
        title="Company register",
        description="State register of legal entities with IDNO and cross references.",
        url="/v1/companies/search",
        source="Companies",
    ),
    SearchResult(
        title="NGO register",
        description="Non-profit organization registry entries and lookups.",
        url="/v1/ngos/search",
        source="NGOs",
    ),
    SearchResult(
        title="Official Gazette",
        description="Monitorul Oficial editions and article snippets.",
        url="/v1/legislation/search",
        source="Legislation",
    ),
    SearchResult(
        title="Geospatial layers",
        description="Open geo layers, cadastre extracts, and raion boundaries.",
        url="/v1/geospatial/layers",
        source="Geospatial",
    ),
    SearchResult(
        title="Weather current",
        description="Weather endpoint ready for meteo.md integration.",
        url="/v1/weather/current",
        source="Meteo",
    ),
]


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


def _matches(query: str, *values: Iterable[str | None] | str | None) -> bool:
    if not query:
        return True
    needle = normalize_query(query)
    haystacks: list[str] = []
    for value in values:
        if value is None:
            continue
        if isinstance(value, str):
            haystacks.append(value)
        else:
            for item in value:
                if item:
                    haystacks.append(item)
    return any(needle in normalize_query(str(value)) for value in haystacks if value)


def build_global_search_results(query: str = "", *, session: Session | None = None) -> list[SearchResult]:
    items: list[SearchResult] = []
    normalized = normalize_query(query)

    for item in STATIC_CATALOG:
        if not normalized or _matches(normalized, item.title, item.description, item.source):
            items.append(item)

    with _session_scope(session) as db:
        datasets = list_datasets(query=query or None, sync_if_empty=False, session=db)
        for dataset in datasets[:30]:
            if normalized and not _matches(normalized, dataset.title, dataset.notes, dataset.organization, dataset.tags):
                continue
            items.append(
                SearchResult(
                    title=dataset.title,
                    description=dataset.notes or f"CKAN dataset from {dataset.organization or 'dataset.gov.md/en'}",
                    url=f"/v1/datasets/{dataset.dataset_id}",
                    source=dataset.organization or "CKAN",
                )
            )

        for entity in list_entities("company", query=query or None, sync_if_empty=False, session=db)[:20]:
            if normalized and not _matches(normalized, entity.name, entity.identifier_value, entity.raion, entity.description):
                continue
            items.append(
                SearchResult(
                    title=entity.name,
                    description=entity.description or f"Company register entry {entity.identifier_value or entity.entity_id}",
                    url=f"/v1/companies/{entity.entity_id}",
                    source="Companies",
                )
            )

        for entity in list_entities("ngo", query=query or None, sync_if_empty=False, session=db)[:20]:
            if normalized and not _matches(normalized, entity.name, entity.identifier_value, entity.raion, entity.description):
                continue
            items.append(
                SearchResult(
                    title=entity.name,
                    description=entity.description or f"NGO register entry {entity.identifier_value or entity.entity_id}",
                    url=f"/v1/ngos/{entity.entity_id}",
                    source="NGOs",
                )
            )

        for edition in list_editions(query=query or None, sync_if_empty=False, session=db)[:20]:
            if normalized and not _matches(normalized, edition.edition_number, edition.title, edition.summary):
                continue
            items.append(
                SearchResult(
                    title=edition.title,
                    description=edition.summary or f"Monitorul Oficial edition {edition.edition_number}",
                    url=f"/v1/legislation/{edition.edition_key}",
                    source="Legislation",
                )
            )

        for article in list_articles(query=query or None, sync_if_empty=False, session=db)[:20]:
            if normalized and not _matches(normalized, article.title, article.content_snippet, article.article_number):
                continue
            items.append(
                SearchResult(
                    title=article.title,
                    description=article.content_snippet,
                    url=f"/v1/legislation/{article.edition_key}",
                    source="Legislation",
                )
            )

        for layer in list_layers(query=query or None, sync_if_empty=False, session=db)[:20]:
            if normalized and not _matches(normalized, layer.title, layer.description, layer.source_type):
                continue
            items.append(
                SearchResult(
                    title=layer.title,
                    description=layer.description or f"{layer.source_type} geospatial layer",
                    url=f"/v1/geospatial/layers/{layer.layer_key}",
                    source="Geospatial",
                )
            )

        for tender in list_tenders(query=query or None, sync_if_empty=False, session=db)[:20]:
            if normalized and not _matches(normalized, tender.title, tender.description, tender.buyer.name, tender.buyer.sector):
                continue
            items.append(
                SearchResult(
                    title=tender.title,
                    description=tender.description or tender.buyer.name,
                    url=f"/v1/procurement/tenders/{tender.ocid}",
                    source="MTender",
                )
            )

        for project in list_projects(sync_if_empty=False, session=db)[:20]:
            if normalized and not _matches(normalized, project.title, project.description, project.sector, project.beneficiary):
                continue
            items.append(
                SearchResult(
                    title=project.title,
                    description=project.description,
                    url=f"/v1/eu-funds/projects/{project.id}",
                    source="EU Funds",
                )
            )

    seen: set[tuple[str, str]] = set()
    deduped: list[SearchResult] = []
    for item in items:
        key = (item.title.lower(), item.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped
