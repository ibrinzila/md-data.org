from fastapi import APIRouter, HTTPException, Query

from src.api.v1.schemas import EUFundingStatistics, EUProject
from src.services import eu_funds_ingest

router = APIRouter()


@router.get("/projects", response_model=list[EUProject])
async def list_projects(
    status: str | None = Query(default=None),
    sector: str | None = Query(default=None),
    raion: str | None = Query(default=None),
) -> list[EUProject]:
    return eu_funds_ingest.list_projects(status=status, sector=sector, raion=raion)


@router.get("/projects/{project_id}", response_model=EUProject)
async def project_detail(project_id: str) -> EUProject:
    project = eu_funds_ingest.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="EU project not found")
    return project


@router.get("/statistics", response_model=EUFundingStatistics)
async def funding_statistics() -> EUFundingStatistics:
    return eu_funds_ingest.get_statistics()
