from datetime import date
import xml.etree.ElementTree as ET

import httpx
from fastapi import APIRouter

from src.api.v1.schemas import ExchangeRate

router = APIRouter()


@router.get("/exchange-rates")
async def get_exchange_rates() -> dict[str, object]:
    url = f"http://www.bnm.md/en/official_exchange_rates?get_xml=1&date={date.today().strftime('%d.%m.%Y')}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            root = ET.fromstring(response.text)
            rates: list[ExchangeRate] = []
            for valute in root.findall(".//Valute"):
                currency = valute.findtext("CharCode")
                raw_value = valute.findtext("Value")
                if not currency or not raw_value:
                    continue
                rates.append(
                    ExchangeRate(
                        currency=currency,
                        value=float(raw_value.replace(",", ".")),
                    )
                )
            return {
                "date": date.today().isoformat(),
                "base": "MDL",
                "source": url,
                "source_status": "live",
                "rates": rates,
            }
    except Exception:
        return {
            "date": date.today().isoformat(),
            "base": "MDL",
            "source": url,
            "source_status": "fallback",
            "rates": [
                ExchangeRate(currency="EUR", value=19.5),
                ExchangeRate(currency="USD", value=17.9),
            ],
        }

