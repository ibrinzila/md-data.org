from fastapi import APIRouter, HTTPException, Query

from src.api.v1.schemas import RegistryEntity
from src.services.registry_ingest import get_entity, list_entities

router = APIRouter()


@router.get("/search")
async def search_companies(q: str = Query(..., description="IDNO or name"), limit: int = Query(default=50, ge=1, le=200)) -> dict[str, object]:
    results = list_entities("company", query=q)
    return {"query": q, "count": len(results), "results": results[:limit]}


@router.get("/{idno}", response_model=RegistryEntity)
async def get_company(idno: str) -> RegistryEntity:
    company = get_entity("company", idno)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company
