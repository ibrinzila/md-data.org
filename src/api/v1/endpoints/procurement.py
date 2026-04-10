from fastapi import APIRouter, HTTPException, Query

from src.api.v1.schemas import (
    ProcurementAward,
    ProcurementBudget,
    ProcurementContract,
    ProcurementPlan,
    ProcurementStatistics,
    ProcurementTender,
)
from src.services import mtender_ingest

router = APIRouter()


@router.get("/tenders", response_model=list[ProcurementTender])
async def list_tenders(
    raion: str | None = Query(default=None),
    status: str | None = Query(default=None),
    query: str | None = Query(default=None),
) -> list[ProcurementTender]:
    return mtender_ingest.list_tenders(raion=raion, status=status, query=query)


@router.get("/tenders/{ocid}", response_model=ProcurementTender)
async def tender_detail(ocid: str) -> ProcurementTender:
    tender = mtender_ingest.get_tender(ocid)
    if tender is None:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender


@router.get("/awards", response_model=list[ProcurementAward])
async def list_awards(raion: str | None = Query(default=None)) -> list[ProcurementAward]:
    return mtender_ingest.list_awards(raion=raion)


@router.get("/contracts", response_model=list[ProcurementContract])
async def list_contracts(raion: str | None = Query(default=None)) -> list[ProcurementContract]:
    return mtender_ingest.list_contracts(raion=raion)


@router.get("/budgets", response_model=list[ProcurementBudget])
async def list_budgets(raion: str | None = Query(default=None)) -> list[ProcurementBudget]:
    return mtender_ingest.list_budgets(raion=raion)


@router.get("/plans", response_model=list[ProcurementPlan])
async def list_plans(raion: str | None = Query(default=None)) -> list[ProcurementPlan]:
    return mtender_ingest.list_plans(raion=raion)


@router.get("/statistics", response_model=ProcurementStatistics)
async def procurement_statistics(raion: str | None = Query(default=None)) -> ProcurementStatistics:
    return mtender_ingest.get_statistics(raion=raion)
