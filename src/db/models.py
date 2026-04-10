from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class SourceRecord(Base):
    __tablename__ = "source_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProcurementTenderRecord(Base):
    __tablename__ = "procurement_tenders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ocid: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status_detail: Mapped[str | None] = mapped_column(String(128), nullable=True)
    date_published: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="MDL")
    raion: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    buyer_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    buyer_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    buyer_sector: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    procurement_method: Mapped[str | None] = mapped_column(String(120), nullable=True)
    procedure_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    classification_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    classification_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_collection: Mapped[str] = mapped_column(String(40), nullable=False, default="tenders")
    source_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cross_references: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ProcurementAwardRecord(Base):
    __tablename__ = "procurement_awards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ocid: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    tender_ocid: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="MDL")
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    buyer_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    buyer_sector: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    raion: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_collection: Mapped[str] = mapped_column(String(40), nullable=False, default="contracts")
    source_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ProcurementContractRecord(Base):
    __tablename__ = "procurement_contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ocid: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    award_ocid: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tender_ocid: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="MDL")
    supplier_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    buyer_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    buyer_sector: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    raion: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_collection: Mapped[str] = mapped_column(String(40), nullable=False, default="contracts")
    source_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ProcurementBudgetRecord(Base):
    __tablename__ = "procurement_budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="MDL")
    raion: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    buyer_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    buyer_sector: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    planning_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    planning_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_collection: Mapped[str] = mapped_column(String(40), nullable=False, default="budgets")
    source_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ProcurementPlanRecord(Base):
    __tablename__ = "procurement_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ocid: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    raion: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    buyer_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    buyer_sector: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="MDL")
    pin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    related_tender_ocids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_collection: Mapped[str] = mapped_column(String(40), nullable=False, default="plans")
    source_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class EUProjectRecord(Base):
    __tablename__ = "eu_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sector: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    raw_sector: Mapped[str | None] = mapped_column(String(255), nullable=True)
    priority_area: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subsector: Mapped[str | None] = mapped_column(String(255), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(255), nullable=True)
    countries: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    funding_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="EUR")
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    beneficiary: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    raion: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    region_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    project_number: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    social_links: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    linked_procurement_ocids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_collection: Mapped[str] = mapped_column(String(40), nullable=False, default="eu-projects")
    source_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class CKANDatasetRecord(Base):
    __tablename__ = "ckan_datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dataset_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    resources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class RegistryEntityRecord(Base):
    __tablename__ = "registry_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raion: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    locality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    identifier_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    identifier_value: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    source_dataset_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    cross_references: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class LegislationEditionRecord(Base):
    __tablename__ = "legislation_editions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    edition_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    edition_number: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class LegislationArticleRecord(Base):
    __tablename__ = "legislation_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    edition_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    article_number: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class GeoLayerRecord(Base):
    __tablename__ = "geo_layers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    layer_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    layer_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
