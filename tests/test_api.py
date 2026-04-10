from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "md-data.org" in response.json()["message"]


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_search_catalog() -> None:
    response = client.get("/v1/search")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_procurement_endpoints() -> None:
    tender_list = client.get("/v1/procurement/tenders")
    assert tender_list.status_code == 200
    assert len(tender_list.json()) >= 1

    tender_detail = client.get("/v1/procurement/tenders/ocds-md-2026-0001")
    assert tender_detail.status_code == 200
    assert tender_detail.json()["ocid"] == "ocds-md-2026-0001"

    stats = client.get("/v1/procurement/statistics?raion=Chisinau")
    assert stats.status_code == 200
    assert stats.json()["by_raion"]["Chisinau"]["currency"] == "MDL"


def test_eu_funds_endpoints() -> None:
    projects = client.get("/v1/eu-funds/projects?raion=Cahul")
    assert projects.status_code == 200
    assert len(projects.json()) >= 1

    project_detail = client.get("/v1/eu-funds/projects/eu4-urban-001")
    assert project_detail.status_code == 200
    assert project_detail.json()["id"] == "eu4-urban-001"

    stats = client.get("/v1/eu-funds/statistics")
    assert stats.status_code == 200
    assert stats.json()["total_projects"] >= 1


def test_definitive_source_endpoints() -> None:
    datasets = client.get("/v1/datasets")
    assert datasets.status_code == 200
    assert any(item["dataset_id"] == "company-register-2026" for item in datasets.json())

    company_search = client.get("/v1/companies/search?q=Example")
    assert company_search.status_code == 200
    assert company_search.json()["count"] >= 1
    assert company_search.json()["results"][0]["entity_type"] == "company"

    ngo_search = client.get("/v1/ngos/search?q=Civic")
    assert ngo_search.status_code == 200
    assert ngo_search.json()["count"] >= 1

    legislation = client.get("/v1/legislation/search?q=Official")
    assert legislation.status_code == 200
    assert legislation.json()["count"] >= 1

    geospatial = client.get("/v1/geospatial/layers?q=Raion")
    assert geospatial.status_code == 200
    assert len(geospatial.json()) >= 1

    global_search = client.get("/v1/search?q=Chisinau")
    assert global_search.status_code == 200
    titles = [item["title"] for item in global_search.json()]
    assert any("Chisinau" in title for title in titles)


def test_status_page() -> None:
    response = client.get("/status")
    assert response.status_code == 200
    assert "md-data.org / status" in response.text
    assert "Explore the data, not the endpoints." in response.text
    assert "/status/data" in response.text


def test_status_data(monkeypatch) -> None:
    async def fake_exchange_rates() -> dict[str, object]:
        return {
            "date": "2026-04-10",
            "base": "MDL",
            "source": "https://example.test/bnm.xml",
            "source_status": "live",
            "rates": [{"currency": "EUR", "value": 19.5}],
        }

    monkeypatch.setattr("src.api.status.get_exchange_rates", fake_exchange_rates)

    response = client.get("/status/data")
    assert response.status_code == 200

    payload = response.json()
    assert payload["overall"]["label"] == "operational"
    assert payload["summary"][0]["label"] == "Source families"
    assert payload["summary"][0]["value"] == "8"
    assert payload["summary"][1]["label"] == "Scenarios"
    assert int(payload["summary"][1]["value"]) >= 6
    assert payload["summary"][2]["label"] == "Live families"
    assert payload["bridge"]["count"] == 2
    assert any(module["id"] == "procurement" for module in payload["sources"])
    assert len(payload["scenarios"]) >= 6
