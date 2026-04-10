from fastapi import APIRouter, HTTPException, Query

from src.api.v1.schemas import GeoLayer
from src.services.geospatial_ingest import get_layer, list_layers, search_layers

router = APIRouter()


@router.get("/layers", response_model=list[GeoLayer])
async def get_geo_layers(q: str = Query(default=""), limit: int = Query(default=100, ge=1, le=300)) -> list[GeoLayer]:
    if q:
        items = search_layers(q)
    else:
        items = list_layers()
    return items[:limit]


@router.get("/layers/{layer_key}", response_model=GeoLayer)
async def get_geo_layer(layer_key: str) -> GeoLayer:
    layer = get_layer(layer_key)
    if layer is None:
        raise HTTPException(status_code=404, detail="Geospatial layer not found")
    return layer


@router.get("/cadastre/search")
async def search_cadastre(q: str = Query(..., description="Search geo layers and cadastre extracts")) -> dict[str, object]:
    results = search_layers(q)
    return {"query": q, "count": len(results), "results": results}
