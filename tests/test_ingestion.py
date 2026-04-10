from datetime import datetime, timezone

from src.db import session as db_session
from src.db.models import EUProjectRecord, ProcurementTenderRecord
from src.services import eu_funds_ingest, mtender_ingest


def test_mtender_sync_persists_records(monkeypatch) -> None:
    def fake_fetch_collection(collection: str, page: int = 1, page_size: int = 10, query: str | None = None):
        if collection == "tenders":
            return {
                "data": [
                    {
                        "id": "ocds-live-0001",
                        "entityId": "ocds-live-0001",
                        "title": "Edinet road maintenance",
                        "description": "Road maintenance in Edinet",
                        "buyerRegion": "Edinet",
                        "procedureType": "openTender",
                        "amount": 1111,
                        "currency": "MDL",
                        "modifiedDate": "2026-04-10T15:00:00Z",
                        "buyerName": "Edinet Municipality",
                        "procedureStatus": "active",
                        "procedureOwnership": "government",
                    }
                ]
            }
        if collection == "contracts":
            return {
                "data": [
                    {
                        "id": "contract-live-0001",
                        "entityId": "ocds-live-0001",
                        "title": "Edinet road maintenance",
                        "description": "Road maintenance contract",
                        "buyerRegion": "Edinet",
                        "procedureType": "openTender",
                        "amount": 1111,
                        "currency": "MDL",
                        "modifiedDate": "2026-04-10T16:00:00Z",
                        "buyerName": "Edinet Municipality",
                        "tags": ["award"],
                        "procedureStatus": "active",
                    }
                ]
            }
        if collection == "budgets":
            return {
                "data": [
                    {
                        "id": "budget-live-0001",
                        "entityId": "ocds-live-0001",
                        "title": "Edinet road maintenance budget",
                        "description": "",
                        "buyerRegion": "Edinet",
                        "budgetStatus": "planning",
                        "amount": 1111,
                        "currency": "MDL",
                        "periodPlanningFrom": "2026-01-01T00:00:00Z",
                        "periodPlanningTo": "2026-12-31T00:00:00Z",
                        "modifiedDate": "2026-04-10T16:00:00Z",
                        "buyerName": "Edinet Municipality",
                    }
                ]
            }
        if collection == "plans":
            return {
                "data": [
                    {
                        "id": "plan-live-0001",
                        "entityId": "ocds-live-0001",
                        "title": "Edinet road maintenance plan",
                        "description": "Planning notice",
                        "buyerRegion": "Edinet",
                        "procedureType": "openTender",
                        "amount": 1111,
                        "currency": "MDL",
                        "modifiedDate": "2026-04-10T16:00:00Z",
                        "buyerName": "Edinet Municipality",
                        "tags": ["planning"],
                        "pin": "false",
                    }
                ]
            }
        raise AssertionError(collection)

    def fake_fetch_detail(ocid: str):
        assert ocid == "ocds-live-0001"
        return {
            "records": [
                {
                    "compiledRelease": {
                        "ocid": ocid,
                        "date": "2026-04-10T15:00:00Z",
                        "planning": {
                            "budget": {
                                "amount": {"amount": 1111, "currency": "MDL"},
                                "isEuropeanUnionFunded": False,
                            }
                        },
                        "tender": {
                            "title": "Edinet road maintenance",
                            "description": "Road maintenance in Edinet",
                            "status": "active",
                            "statusDetails": "tendering",
                            "value": {"amount": 1111, "currency": "MDL"},
                            "procurementMethod": "open",
                            "procurementMethodDetails": "openTender",
                            "mainProcurementCategory": "works",
                            "procuringEntity": {"id": "md.edinet", "name": "Edinet Municipality"},
                            "classification": {
                                "scheme": "CPV",
                                "id": "45233120-6",
                                "description": "Road construction works",
                            },
                        },
                        "parties": [
                            {
                                "id": "md.edinet",
                                "name": "Edinet Municipality",
                                "address": {
                                    "addressDetails": {
                                        "region": {"description": "Edinet"},
                                        "locality": {"description": "Edinet"},
                                    }
                                },
                            }
                        ],
                    }
                }
            ],
            "publishedDate": "2026-04-10T15:00:00Z",
        }

    monkeypatch.setattr(mtender_ingest, "fetch_mtender_collection", fake_fetch_collection)
    monkeypatch.setattr(mtender_ingest, "fetch_mtender_detail", fake_fetch_detail)

    result = mtender_ingest.sync_mtender_database(tender_pages=1, contract_pages=1, budget_pages=1, plan_pages=1)
    assert result["tenders"] == 1
    assert result["awards"] == 1
    assert result["contracts"] == 1
    assert result["budgets"] == 1
    assert result["plans"] == 1

    with db_session.SessionLocal() as session:
        tender = session.query(ProcurementTenderRecord).filter_by(ocid="ocds-live-0001").one()
        assert tender.buyer_sector == "Infrastructure"
        assert "eu4-urban-001" in tender.cross_references["eu_project_ids"]

        project = session.query(EUProjectRecord).filter_by(project_id="eu4-urban-001").one()
        assert "ocds-live-0001" in project.linked_procurement_ocids


def test_eu_sync_persists_records(monkeypatch) -> None:
    def fake_fetch_projects_page(page: int = 1):
        assert page == 1
        return [
            {
                "project_id": "eu-live-0001",
                "title": "Green schools in Edinet",
                "start_date": datetime(2026, 1, 1, tzinfo=timezone.utc),
                "end_date": datetime(2027, 1, 1, tzinfo=timezone.utc),
                "source_url": "https://eu4moldova.eu/en/projects/eu-project-page/?id=9999",
                "listing_text": "Green schools in Edinet Start Date 01.01.2026 End Date 01.01.2027",
            }
        ]

    def fake_fetch_project_detail(url: str):
        assert "id=9999" in url
        return {
            "title": "Green schools in Edinet",
            "description": "Energy-efficient school upgrades in Edinet.",
            "priority_area": "Human development",
            "subsector": "Education",
            "topic": "Schools",
            "countries": ["Republic of Moldova"],
            "status": "ongoing",
            "start_date": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "end_date": datetime(2027, 1, 1, tzinfo=timezone.utc),
            "project_number": "EU-LIVE-001",
            "website_url": "https://example.test/education",
            "social_links": [],
            "region_label": "Regional",
            "sector": "Education",
            "raw_text": "Project details text",
            "specific_objective": "Improve learning environments.",
            "expected_results": "Modernized classrooms.",
        }

    monkeypatch.setattr(eu_funds_ingest, "fetch_eu_projects_page", fake_fetch_projects_page)
    monkeypatch.setattr(eu_funds_ingest, "fetch_eu_project_detail", fake_fetch_project_detail)

    result = eu_funds_ingest.sync_eu_funds_database(max_pages=1)
    assert result["projects"] == 1

    with db_session.SessionLocal() as session:
        project = session.query(EUProjectRecord).filter_by(project_id="eu-live-0001").one()
        assert project.sector == "Education"
        assert "ocds-md-2026-0002" in project.linked_procurement_ocids

        tender = session.query(ProcurementTenderRecord).filter_by(ocid="ocds-md-2026-0002").one()
        assert "eu-live-0001" in tender.cross_references["eu_project_ids"]
