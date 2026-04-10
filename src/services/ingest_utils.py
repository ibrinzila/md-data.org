from __future__ import annotations

import re
from datetime import date, datetime, time, timezone
from typing import Any, Iterable

from src.services.normalizer import normalize_query

SECTOR_KEYWORDS: list[tuple[str, str]] = [
    ("medic", "Health"),
    ("health", "Health"),
    ("hospital", "Health"),
    ("school", "Education"),
    ("education", "Education"),
    ("university", "Education"),
    ("digital", "IT"),
    ("software", "IT"),
    ("it ", "IT"),
    ("information technology", "IT"),
    ("road", "Infrastructure"),
    ("bridge", "Infrastructure"),
    ("transport", "Infrastructure"),
    ("connectivity", "Infrastructure"),
    ("energy", "Infrastructure"),
    ("water", "Infrastructure"),
    ("sanitation", "Infrastructure"),
    ("construction", "Infrastructure"),
    ("climate", "Environment"),
    ("environment", "Environment"),
    ("agric", "Agriculture"),
    ("food", "Agriculture"),
    ("enterprise", "Economy"),
    ("business", "Economy"),
    ("sme", "Economy"),
    ("justice", "Governance"),
    ("corruption", "Governance"),
    ("police", "Governance"),
    ("migration", "Governance"),
    ("civil society", "Governance"),
    ("gender", "Social"),
    ("child", "Social"),
    ("social", "Social"),
    ("media", "Media"),
    ("communication", "Media"),
    ("culture", "Culture"),
    ("tourism", "Culture"),
]


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    raw = value.strip()
    candidates = (
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y",
        "%Y-%m-%d",
    )
    for candidate in candidates:
        try:
            parsed = datetime.strptime(raw, candidate)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_ddmmyyyy(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%d.%m.%Y")
    except ValueError:
        return parse_datetime(value)
    return parsed.replace(tzinfo=timezone.utc)


def parse_bool(value: str | bool | None) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def unique_list(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def infer_sector(*texts: str | None) -> str:
    haystack = normalize_query(" ".join(clean_text(text) for text in texts if text))
    if not haystack:
        return "General"
    for needle, sector in SECTOR_KEYWORDS:
        if needle in haystack:
            return sector
    return "General"


def date_to_datetime(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: json_safe(inner) for key, inner in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc).isoformat()
    return value
