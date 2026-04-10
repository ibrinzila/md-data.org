from fastapi import APIRouter, Query

from src.api.v1.schemas import SearchResult
from src.services.normalizer import normalize_query

router = APIRouter()

CATALOG = [
    SearchResult(
        title="BNM exchange rates",
        description="Official exchange-rate endpoint backed by BNM XML.",
        url="/v1/finance/exchange-rates",
        source="BNM",
    ),
    SearchResult(
        title="MTender tenders",
        description="Public procurement feed placeholder linked to the MTender portal.",
        url="/v1/procurement/tenders",
        source="MTender",
    ),
    SearchResult(
        title="Weather current",
        description="Simple weather endpoint ready for meteo.md integration.",
        url="/v1/weather/current",
        source="Meteo",
    ),
]


@router.get("", response_model=list[SearchResult])
async def search_sources(q: str = Query(default="")) -> list[SearchResult]:
    query = normalize_query(q)
    if not query:
        return CATALOG
    return [
        item
        for item in CATALOG
        if query in normalize_query(item.title)
        or query in normalize_query(item.description)
        or query in normalize_query(item.source)
    ]

