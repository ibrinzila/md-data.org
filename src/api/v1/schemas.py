from datetime import datetime
from typing import Any, Optional

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


class OCDSAmount(BaseModel):
    amount: float
    currency: str = "MDL"


class BuyerReference(BaseModel):
    id: str
    name: str
    sector: Optional[str] = None


class ProcurementTender(BaseModel):
    ocid: str
    title: str
    description: Optional[str] = None
    status: str
    date_published: datetime
    value: Optional[OCDSAmount] = None
    location: Optional[Location] = None
    buyer: BuyerReference
    cross_references: dict[str, Any] = Field(default_factory=dict)


class ProcurementAward(BaseModel):
    ocid: str
    tender_ocid: str
    title: str
    status: str
    value: Optional[OCDSAmount] = None
    supplier_name: Optional[str] = None
    raion: Optional[str] = None


class ProcurementContract(BaseModel):
    ocid: str
    award_ocid: str
    title: str
    status: str
    signed_at: datetime
    value: Optional[OCDSAmount] = None
    supplier_name: Optional[str] = None
    raion: Optional[str] = None


class ProcurementBudget(BaseModel):
    code: str
    name: str
    amount: OCDSAmount
    raion: Optional[str] = None


class ProcurementPlan(BaseModel):
    ocid: str
    title: str
    status: str
    raion: Optional[str] = None
    related_tender_ocids: list[str] = Field(default_factory=list)


class ProcurementStatistics(BaseModel):
    total_tenders: int
    total_awards: int
    total_contracts: int
    total_budget: OCDSAmount
    by_raion: dict[str, OCDSAmount]
    top_sectors: list[str]


class EUProject(BaseModel):
    id: str
    title: str
    description: str
    status: str
    sector: str
    funding_amount: Optional[OCDSAmount] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    beneficiary: Optional[str] = None
    location: Optional[Location] = None
    linked_procurement_ocids: list[str] = Field(default_factory=list)


class EUFundingStatistics(BaseModel):
    total_projects: int
    total_funding: OCDSAmount
    by_sector: dict[str, OCDSAmount]
    by_raion: dict[str, OCDSAmount]


class CKANDataset(BaseModel):
    dataset_id: str
    title: str
    slug: str
    notes: Optional[str] = None
    organization: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    resources: list[dict[str, Any]] = Field(default_factory=list)
    source_url: str
    source_modified_at: Optional[datetime] = None


class RegistryEntity(BaseModel):
    entity_key: str
    entity_type: str
    entity_id: str
    name: str
    status: Optional[str] = None
    description: Optional[str] = None
    raion: Optional[str] = None
    locality: Optional[str] = None
    identifier_label: Optional[str] = None
    identifier_value: Optional[str] = None
    source_dataset_id: Optional[str] = None
    source_url: str
    cross_references: dict[str, Any] = Field(default_factory=dict)


class LegislationEdition(BaseModel):
    edition_key: str
    edition_number: str
    title: str
    published_at: Optional[datetime] = None
    pdf_url: Optional[str] = None
    source_url: str
    summary: Optional[str] = None


class LegislationArticle(BaseModel):
    article_key: str
    edition_key: str
    article_number: Optional[str] = None
    title: str
    content_snippet: str
    source_url: str


class GeoLayer(BaseModel):
    layer_key: str
    title: str
    description: Optional[str] = None
    source_type: str
    source_url: str
    metadata: dict[str, Any] = Field(default_factory=dict)
