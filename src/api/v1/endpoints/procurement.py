from fastapi import APIRouter

from src.api.v1.schemas import TenderSummary

router = APIRouter()


@router.get("/tenders", response_model=list[TenderSummary])
async def list_tenders() -> list[TenderSummary]:
    return [
        TenderSummary(
            title="MTender feed placeholder",
            status="available",
            source_url="https://public.mtender.gov.md/tenders",
        )
    ]

