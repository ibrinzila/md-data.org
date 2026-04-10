from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Location(BaseModel):
    raion: str
    city: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class WeatherCurrent(BaseModel):
    temperature: float
    condition: str
    location: Location
    last_updated: datetime


class EmergencyAlert(BaseModel):
    title: str
    severity: str = Field(default="info")
    region: str
    description: str
    source_url: Optional[str] = None


class TenderSummary(BaseModel):
    title: str
    status: str
    source_url: str


class StatisticItem(BaseModel):
    indicator: str
    value: str
    unit: Optional[str] = None
    source_url: Optional[str] = None


class ExchangeRate(BaseModel):
    currency: str
    value: float


class SearchResult(BaseModel):
    title: str
    description: str
    url: str
    source: str

