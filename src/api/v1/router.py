from fastapi import APIRouter

from .endpoints import companies, datasets, emergencies, eu_funds, finance, geospatial, legislation, ngos, procurement, search, statistics, weather

api_router = APIRouter()

api_router.include_router(weather.router, prefix="/weather", tags=["Weather"])
api_router.include_router(emergencies.router, prefix="/emergencies", tags=["Emergencies"])
api_router.include_router(procurement.router, prefix="/procurement", tags=["Procurement"])
api_router.include_router(statistics.router, prefix="/statistics", tags=["Statistics"])
api_router.include_router(finance.router, prefix="/finance", tags=["Finance"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["Datasets"])
api_router.include_router(companies.router, prefix="/companies", tags=["Companies"])
api_router.include_router(ngos.router, prefix="/ngos", tags=["NGOs"])
api_router.include_router(legislation.router, prefix="/legislation", tags=["Legislation"])
api_router.include_router(geospatial.router, prefix="/geospatial", tags=["Geospatial"])
api_router.include_router(eu_funds.router, prefix="/eu-funds", tags=["EU Funds"])

router = api_router
