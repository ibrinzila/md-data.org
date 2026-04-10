from fastapi import APIRouter, HTTPException, Query

from src.api.v1.schemas import CKANDataset
from src.services.ckan_ingest import get_dataset, list_datasets

router = APIRouter()


@router.get("", response_model=list[CKANDataset])
async def datasets(q: str = Query(default=""), limit: int = Query(default=50, ge=1, le=200)) -> list[CKANDataset]:
    items = list_datasets(query=q or None)
    return items[:limit]


@router.get("/{dataset_id}", response_model=CKANDataset)
async def dataset_detail(dataset_id: str) -> CKANDataset:
    dataset = get_dataset(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset
