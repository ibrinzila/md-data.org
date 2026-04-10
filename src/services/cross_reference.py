from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models import EUProjectRecord, ProcurementTenderRecord
from src.services.normalizer import normalize_query


def rebuild_cross_references(session: Session) -> dict[str, int]:
    session.flush()
    tenders = session.scalars(select(ProcurementTenderRecord)).all()
    projects = session.scalars(select(EUProjectRecord)).all()

    project_links: dict[str, set[str]] = {
        project.project_id: set(project.linked_procurement_ocids or []) for project in projects
    }
    tender_links: dict[str, set[str]] = {
        tender.ocid: set((tender.cross_references or {}).get("eu_project_ids", [])) for tender in tenders
    }

    for project in projects:
        project_sector = normalize_query(project.sector or "")
        project_raion = normalize_query(project.raion or "")

        for tender in tenders:
            tender_sector = normalize_query(tender.buyer_sector or "")
            tender_raion = normalize_query(tender.raion or "")

            matched = False
            if project_raion and tender_raion and project_raion == tender_raion:
                matched = True
            elif project_sector and tender_sector and project_sector == tender_sector:
                matched = True

            if not matched:
                continue

            project_links.setdefault(project.project_id, set()).add(tender.ocid)
            tender_links.setdefault(tender.ocid, set()).add(project.project_id)

    for project in projects:
        project.linked_procurement_ocids = sorted(project_links.get(project.project_id, set()))
        session.add(project)

    for tender in tenders:
        refs = dict(tender.cross_references or {})
        refs["eu_project_ids"] = sorted(tender_links.get(tender.ocid, set()))
        tender.cross_references = refs
        session.add(tender)

    session.commit()

    return {
        "tenders": len(tenders),
        "projects": len(projects),
        "links": sum(len(ids) for ids in project_links.values()),
    }
