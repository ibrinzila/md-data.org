from fastapi import APIRouter

from src.api.v1.schemas import StatisticItem

router = APIRouter()


@router.get("/summary", response_model=list[StatisticItem])
async def get_statistics_summary() -> list[StatisticItem]:
    return [
        StatisticItem(
            indicator="Source",
            value="NBS Statbank PxWeb",
            unit=None,
            source_url="https://statbank.statistica.md/",
        )
    ]

