from fastapi import APIRouter, Query

from src.api.v1.schemas import SearchResult
from src.services.discovery import build_global_search_results
from src.services.normalizer import normalize_query

router = APIRouter()


@router.get("", response_model=list[SearchResult])
async def search_sources(q: str = Query(default="")) -> list[SearchResult]:
    query = normalize_query(q)
    return build_global_search_results(query)
