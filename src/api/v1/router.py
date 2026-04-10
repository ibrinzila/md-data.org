from fastapi import APIRouter

from .endpoints import emergencies, finance, procurement, search, statistics, weather

api_router = APIRouter()

api_router.include_router(weather.router, prefix="/weather", tags=["Weather"])
api_router.include_router(emergencies.router, prefix="/emergencies", tags=["Emergencies"])
api_router.include_router(procurement.router, prefix="/procurement", tags=["Procurement"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["Statistics"])
api_router.include_router(finance.router, prefix="/finance", tags=["Finance"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])

router = api_router

