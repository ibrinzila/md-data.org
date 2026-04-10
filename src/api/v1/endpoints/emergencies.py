from fastapi import APIRouter

from src.api.v1.schemas import EmergencyAlert

router = APIRouter()


@router.get("/alerts", response_model=list[EmergencyAlert])
async def get_emergency_alerts() -> list[EmergencyAlert]:
    return [
        EmergencyAlert(
            title="No active alerts",
            severity="info",
            region="Moldova",
            description="Placeholder emergency feed ready for IGSU integration.",
            source_url="https://dse.md/",
        )
    ]

