from datetime import datetime

from fastapi import APIRouter

from src.api.v1.schemas import Location, WeatherCurrent

router = APIRouter()


@router.get("/current", response_model=WeatherCurrent)
async def get_current_weather(city: str = "Chisinau") -> WeatherCurrent:
    return WeatherCurrent(
        temperature=21.5,
        condition="clear",
        location=Location(raion="Chisinau", city=city, lat=47.0105, lon=28.8638),
        last_updated=datetime.utcnow(),
    )

