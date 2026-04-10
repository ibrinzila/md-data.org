from fastapi import APIRouter, HTTPException, Query

from src.api.v1.schemas import RegistryEntity
from src.services.registry_ingest import get_entity, list_entities

router = APIRouter()


@router.get("/search")
async def search_ngos(q: str = Query(..., description="Registry ID or name"), limit: int = Query(default=50, ge=1, le=200)) -> dict[str, object]:
    results = list_entities("ngo", query=q)
    return {"query": q, "count": len(results), "results": results[:limit]}


@router.get("/{ngo_id}", response_model=RegistryEntity)
async def get_ngo(ngo_id: str) -> RegistryEntity:
    ngo = get_entity("ngo", ngo_id)
    if ngo is None:
        raise HTTPException(status_code=404, detail="NGO not found")
    return ngo
