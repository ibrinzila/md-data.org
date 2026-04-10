from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.api.v1.endpoints.emergencies import get_emergency_alerts
from src.api.v1.endpoints.eu_funds import funding_statistics, list_projects
from src.api.v1.endpoints.finance import get_exchange_rates
from src.api.v1.endpoints.procurement import (
    list_awards,
    list_budgets,
    list_contracts,
    list_plans,
    list_tenders,
    procurement_statistics,
)
from src.api.v1.endpoints.search import search_sources
from src.api.v1.endpoints.statistics import get_statistics_summary
from src.api.v1.endpoints.weather import get_current_weather

router = APIRouter()
logger = logging.getLogger(__name__)


def _dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_dump(item) for item in value]
    if isinstance(value, tuple):
        return [_dump(item) for item in value]
    if isinstance(value, dict):
        return {key: _dump(item) for key, item in value.items()}
    return value


async def _safe_call(label: str, coro: Any, fallback: Any) -> Any:
    try:
        return await coro
    except Exception:
        logger.exception("status payload component failed: %s", label)
        return fallback


def _format_amount(amount: float | int | None, currency: str | None = None) -> str:
    if amount is None:
        return "—"

    value = float(amount)
    magnitude = abs(value)
    suffix = ""
    divisor = 1.0

    if magnitude >= 1_000_000_000:
        suffix = "B"
        divisor = 1_000_000_000
    elif magnitude >= 1_000_000:
        suffix = "M"
        divisor = 1_000_000
    elif magnitude >= 1_000:
        suffix = "K"
        divisor = 1_000

    scaled = value / divisor
    if suffix:
        return f"{scaled:.1f}{suffix} {currency or ''}".strip()
    if value.is_integer():
        return f"{int(value):,} {currency or ''}".strip()
    return f"{value:,.2f} {currency or ''}".strip()


def _format_decimal(value: float | int | None) -> str:
    if value is None:
        return "—"
    return f"{float(value):,.2f}".rstrip("0").rstrip(".")


def _format_datetime(value: str | None) -> str:
    if not value:
        return "Unknown"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%b %d, %Y %H:%M")
    except ValueError:
        return value


def _make_story(
    *,
    story_id: str,
    kicker: str,
    title: str,
    meta: str,
    value: str,
    blurb: str,
    detail: str,
    route: str,
    route_label: str,
    tags: list[str] | None = None,
    secondary_route: str | None = None,
    secondary_label: str | None = None,
    tone: str = "ready",
) -> dict[str, Any]:
    return {
        "id": story_id,
        "kicker": kicker,
        "title": title,
        "meta": meta,
        "value": value,
        "blurb": blurb,
        "detail": detail,
        "route": route,
        "route_label": route_label,
        "tags": tags or [],
        "secondary_route": secondary_route,
        "secondary_label": secondary_label,
        "tone": tone,
    }


def _bridge_story(tenders: list[dict[str, Any]], projects: list[dict[str, Any]]) -> dict[str, Any]:
    tender_map = {item["ocid"]: item for item in tenders if item.get("ocid")}
    links: list[dict[str, Any]] = []

    for project in projects:
        for ocid in project.get("linked_procurement_ocids", []):
            tender = tender_map.get(ocid)
            if tender:
                links.append({"project": project, "tender": tender})

    if not links:
        return {
            "count": 0,
            "title": "Cross-link spotlight",
            "detail": "No procurement and EU funding pairs are linked yet.",
            "project": None,
            "tender": None,
            "route": "/v1/eu-funds/projects",
            "secondary_route": "/v1/procurement/tenders",
        }

    first = links[0]
    project = first["project"]
    tender = first["tender"]
    total_pairs = len(links)
    shared_tenders = len({item["tender"]["ocid"] for item in links if item["tender"].get("ocid")})
    shared_projects = len({item["project"]["id"] for item in links if item["project"].get("id")})

    return {
        "count": total_pairs,
        "shared_tenders": shared_tenders,
        "shared_projects": shared_projects,
        "title": f"{project['title']} ↔ {tender['title']}",
        "detail": (
            f"{total_pairs} cross-link pair(s) connect {shared_projects} EU project(s) "
            f"to {shared_tenders} procurement tender(s)."
        ),
        "project": {
            "title": project["title"],
            "meta": project.get("raion") or project.get("sector") or "EU project",
            "route": f"/v1/eu-funds/projects/{project['id']}",
        },
        "tender": {
            "title": tender["title"],
            "meta": tender.get("location", {}).get("raion") or tender.get("buyer", {}).get("sector") or "Procurement tender",
            "route": f"/v1/procurement/tenders/{tender['ocid']}",
        },
        "route": f"/v1/eu-funds/projects/{project['id']}",
        "secondary_route": f"/v1/procurement/tenders/{tender['ocid']}",
    }


STATUS_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>md-data.org / status</title>
  <meta name="description" content="Moldova public data API - live explorer for procurement, EU funding, macro signals, and discovery">
  <style>
    @import url("https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap");

    :root {
      color-scheme: dark;
      --bg: #07111a;
      --bg-2: #0b1724;
      --card: rgba(11, 20, 32, 0.78);
      --card-strong: rgba(13, 24, 39, 0.94);
      --card-soft: rgba(255, 255, 255, 0.03);
      --line: rgba(216, 227, 245, 0.12);
      --line-strong: rgba(216, 227, 245, 0.2);
      --paper: #f2ece1;
      --paper-soft: rgba(242, 236, 225, 0.78);
      --text: #f4f6fb;
      --muted: #9caac0;
      --muted-strong: #c5cedd;
      --accent: #76f0bf;
      --accent-2: #f7bf65;
      --accent-3: #85a8ff;
      --danger: #ff8c9a;
      --shadow: 0 24px 90px rgba(0, 0, 0, 0.42);
      --radius-xl: 30px;
      --radius-lg: 22px;
      --radius-md: 16px;
      --radius-sm: 12px;
      --font-display: "Fraunces", "Iowan Old Style", "Palatino Linotype", "Baskerville", serif;
      --font-body: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
      --font-mono: "SFMono-Regular", "Menlo", "Consolas", monospace;
    }

    * { box-sizing: border-box; }

    html, body { min-height: 100%; }

    body {
      margin: 0;
      color: var(--text);
      background:
        radial-gradient(circle at 10% 10%, rgba(118, 240, 191, 0.14), transparent 24%),
        radial-gradient(circle at 90% 12%, rgba(247, 191, 101, 0.14), transparent 24%),
        radial-gradient(circle at 45% 100%, rgba(133, 168, 255, 0.18), transparent 28%),
        linear-gradient(180deg, #08121c 0%, #050a12 100%);
      font-family: var(--font-body);
      overflow-x: hidden;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
      background-size: 84px 84px;
      mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.12));
      opacity: 0.22;
    }

    body::after {
      content: "";
      position: fixed;
      inset: auto -10% -18% auto;
      width: 360px;
      height: 360px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(247, 191, 101, 0.14), transparent 68%);
      filter: blur(8px);
      pointer-events: none;
      opacity: 0.7;
    }

    a { color: inherit; }

    .shell {
      position: relative;
      max-width: 1320px;
      margin: 0 auto;
      padding: 20px 20px 34px;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 18px;
    }

    .brand {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      font-size: 0.76rem;
      font-weight: 700;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: var(--muted-strong);
    }

    .brand-mark {
      width: 12px;
      height: 12px;
      border-radius: 999px;
      background: linear-gradient(135deg, var(--accent), #9fe7ff);
      box-shadow: 0 0 0 6px rgba(118, 240, 191, 0.08);
    }

    .nav {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .nav a {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 12px;
      border-radius: 999px;
      text-decoration: none;
      color: var(--muted-strong);
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid transparent;
      transition: transform 160ms ease, color 160ms ease, border-color 160ms ease, background 160ms ease;
    }

    .nav a:hover {
      color: var(--text);
      transform: translateY(-1px);
      border-color: var(--line-strong);
      background: rgba(255, 255, 255, 0.04);
    }

    .nav a[aria-current="page"] {
      color: var(--text);
      border-color: rgba(118, 240, 191, 0.3);
      background: rgba(118, 240, 191, 0.08);
    }

    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
      gap: 18px;
      border: 1px solid var(--line);
      border-radius: var(--radius-xl);
      background: linear-gradient(180deg, rgba(12, 21, 33, 0.92), rgba(8, 14, 22, 0.96));
      box-shadow: var(--shadow);
      overflow: hidden;
      padding: clamp(22px, 3vw, 34px);
    }

    .hero-copy {
      position: relative;
      z-index: 1;
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-size: 0.7rem;
      font-weight: 700;
      margin-bottom: 14px;
    }

    .eyebrow-dot {
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--accent);
      box-shadow: 0 0 18px rgba(118, 240, 191, 0.9);
    }

    h1, h2, h3, h4 {
      margin: 0;
      font-family: var(--font-display);
      letter-spacing: -0.04em;
    }

    h1 {
      font-size: clamp(2.5rem, 5.6vw, 4.85rem);
      line-height: 0.96;
      max-width: 11ch;
    }

    .lede {
      max-width: 68ch;
      margin: 16px 0 0;
      color: var(--muted);
      font-size: clamp(0.98rem, 1.18vw, 1.08rem);
      line-height: 1.62;
    }

    .hero-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 22px;
      align-items: center;
    }

    .button,
    .toggle,
    .chip,
    .mini-action,
    .story-action {
      border: 0;
      font: inherit;
    }

    .button,
    .chip,
    .mini-action,
    .story-action {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      border-radius: 999px;
      text-decoration: none;
      transition: transform 160ms ease, border-color 160ms ease, background 160ms ease, color 160ms ease;
      cursor: pointer;
      white-space: nowrap;
    }

    .button {
      padding: 11px 16px;
      color: var(--text);
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--line);
    }

    .button.primary {
      background: linear-gradient(135deg, rgba(118, 240, 191, 0.16), rgba(118, 240, 191, 0.08));
      border-color: rgba(118, 240, 191, 0.34);
      color: #dffaf0;
    }

    .button:hover,
    .chip:hover,
    .mini-action:hover,
    .story-action:hover {
      transform: translateY(-1px);
    }

    .toggle {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      color: var(--muted-strong);
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.03);
    }

    .toggle input {
      width: 16px;
      height: 16px;
      accent-color: var(--accent);
    }

    .hero-rail {
      display: grid;
      gap: 12px;
      align-content: start;
    }

    .signal-card,
    .bridge-card,
    .summary-panel,
    .section-card,
    .detail-card,
    .api-index {
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: var(--card);
      backdrop-filter: blur(16px);
      box-shadow: 0 16px 46px rgba(0, 0, 0, 0.24);
    }

    .signal-card {
      padding: 18px;
      display: grid;
      gap: 14px;
    }

    .signal-top {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
    }

    .signal-title {
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--muted);
    }

    .signal-name {
      font-family: var(--font-display);
      font-size: 1.55rem;
      line-height: 1.05;
      margin-top: 8px;
    }

    .signal-body {
      color: var(--muted);
      line-height: 1.6;
      font-size: 0.94rem;
    }

    .signal-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .signal-stat {
      padding: 12px;
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .signal-stat strong {
      display: block;
      font-size: 1rem;
      letter-spacing: -0.03em;
    }

    .signal-stat span {
      display: block;
      color: var(--muted);
      font-size: 0.8rem;
      margin-top: 4px;
      line-height: 1.45;
    }

    .bridge-card {
      padding: 18px;
      display: grid;
      gap: 12px;
      border-left: 4px solid var(--accent-2);
    }

    .bridge-kicker {
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.68rem;
      font-weight: 700;
    }

    .bridge-title {
      font-family: var(--font-display);
      font-size: 1.18rem;
      line-height: 1.15;
    }

    .bridge-detail {
      color: var(--muted);
      line-height: 1.55;
      font-size: 0.92rem;
    }

    .bridge-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .bridge-pill {
      padding: 8px 10px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: var(--muted-strong);
      font-size: 0.8rem;
      text-decoration: none;
    }

    .summary-panel {
      margin-top: 18px;
      padding: 16px;
    }

    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }

    .summary-card {
      min-height: 112px;
      padding: 16px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 10px;
    }

    .summary-value {
      font-size: clamp(1.8rem, 2.8vw, 2.7rem);
      line-height: 1;
      font-weight: 700;
      letter-spacing: -0.06em;
    }

    .summary-label {
      color: var(--muted);
      line-height: 1.45;
      font-size: 0.88rem;
    }

    .explore-bar {
      margin: 18px 0;
      display: grid;
      grid-template-columns: minmax(250px, 0.8fr) minmax(0, 1.2fr);
      gap: 12px;
      align-items: start;
    }

    .search-wrap {
      padding: 14px;
      border-radius: var(--radius-lg);
      background: var(--card);
      border: 1px solid var(--line);
      display: grid;
      gap: 10px;
    }

    .search-wrap label {
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--muted);
    }

    .search-wrap input {
      width: 100%;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.03);
      border-radius: 14px;
      color: var(--text);
      padding: 13px 14px;
      font: inherit;
      outline: none;
    }

    .search-wrap input:focus {
      border-color: rgba(118, 240, 191, 0.45);
      box-shadow: 0 0 0 4px rgba(118, 240, 191, 0.08);
    }

    .search-wrap input::placeholder {
      color: rgba(156, 170, 192, 0.7);
    }

    .chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      padding: 14px;
      border-radius: var(--radius-lg);
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--line);
    }

    .chip {
      padding: 10px 13px;
      color: var(--muted-strong);
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid transparent;
    }

    .chip.active {
      color: var(--text);
      background: rgba(118, 240, 191, 0.1);
      border-color: rgba(118, 240, 191, 0.32);
    }

    .content {
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(320px, 0.62fr);
      gap: 16px;
      align-items: start;
    }

    .section-card {
      padding: 18px;
    }

    .section-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 14px;
      margin-bottom: 14px;
    }

    .section-copy {
      max-width: 72ch;
    }

    .section-kicker {
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 0.68rem;
      font-weight: 700;
      margin-bottom: 8px;
    }

    .section-copy h2 {
      font-size: clamp(1.55rem, 2vw, 2.4rem);
      line-height: 1.04;
      margin-bottom: 10px;
    }

    .section-copy p {
      margin: 0;
      color: var(--muted);
      line-height: 1.6;
    }

    .section-state {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 9px 12px;
      font-size: 0.78rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      font-weight: 700;
      white-space: nowrap;
    }

    .status-live { background: rgba(118, 240, 191, 0.12); color: #adf8dc; }
    .status-ready { background: rgba(133, 168, 255, 0.12); color: #d0dcff; }
    .status-placeholder { background: rgba(247, 191, 101, 0.12); color: #ffe0ad; }
    .status-degraded { background: rgba(255, 140, 154, 0.12); color: #ffbec6; }

    .module-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }

    .module-card {
      position: relative;
      overflow: hidden;
      border-radius: 24px;
      padding: 18px;
      border: 1px solid rgba(255, 255, 255, 0.09);
      background: linear-gradient(180deg, rgba(14, 24, 37, 0.94), rgba(9, 15, 24, 0.98));
      display: grid;
      gap: 14px;
      min-height: 360px;
      box-shadow: 0 16px 42px rgba(0, 0, 0, 0.22);
      animation: rise 600ms ease both;
    }

    .module-card::before {
      content: "";
      position: absolute;
      inset: 0 auto auto 0;
      width: 100%;
      height: 4px;
      background: var(--accent, var(--accent-3));
    }

    .module-card.is-active {
      border-color: rgba(118, 240, 191, 0.34);
      box-shadow: 0 18px 56px rgba(0, 0, 0, 0.3);
    }

    .module-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
    }

    .module-kicker {
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 0.68rem;
      font-weight: 700;
      margin-bottom: 6px;
    }

    .module-card h3 {
      font-size: 1.4rem;
      line-height: 1.1;
      margin-bottom: 8px;
    }

    .module-detail {
      color: var(--muted);
      line-height: 1.56;
      font-size: 0.93rem;
      margin: 0;
    }

    .module-panel {
      display: grid;
      gap: 14px;
      position: relative;
    }

    .metric-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .metric {
      padding: 12px;
      border-radius: 18px;
      border: 1px solid rgba(255, 255, 255, 0.06);
      background: rgba(255, 255, 255, 0.03);
      display: grid;
      gap: 6px;
    }

    .metric strong {
      font-size: 1.12rem;
      letter-spacing: -0.03em;
    }

    .metric span {
      color: var(--muted);
      font-size: 0.8rem;
      line-height: 1.45;
    }

    .highlights {
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 8px;
      color: var(--muted-strong);
      line-height: 1.5;
    }

    .chart {
      display: grid;
      gap: 10px;
    }

    .chart-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.68rem;
      font-weight: 700;
    }

    .chart-bar {
      display: grid;
      grid-template-columns: minmax(90px, 0.9fr) minmax(0, 1.3fr) auto;
      gap: 10px;
      align-items: center;
      font-size: 0.86rem;
    }

    .chart-label {
      color: var(--muted-strong);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .chart-track {
      height: 11px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.06);
      overflow: hidden;
    }

    .chart-fill {
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, rgba(118, 240, 191, 0.95), rgba(133, 168, 255, 0.9));
    }

    .chart-value {
      color: var(--muted);
      font-family: var(--font-mono);
      font-size: 0.78rem;
    }

    .story-list {
      display: grid;
      gap: 10px;
    }

    .story-card {
      width: 100%;
      text-align: left;
      padding: 14px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      color: inherit;
      cursor: pointer;
      display: grid;
      gap: 10px;
      transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
    }

    .story-card:hover,
    .story-card.is-active {
      transform: translateY(-1px);
      border-color: rgba(118, 240, 191, 0.28);
      background: rgba(118, 240, 191, 0.06);
    }

    .story-top {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
    }

    .story-kicker {
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.64rem;
      font-weight: 700;
      margin-bottom: 4px;
    }

    .story-title {
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.2;
      margin-bottom: 6px;
    }

    .story-meta {
      color: var(--muted);
      font-size: 0.84rem;
      line-height: 1.45;
    }

    .story-value {
      color: #e9fff8;
      font-family: var(--font-display);
      font-size: 1.02rem;
      letter-spacing: -0.02em;
      white-space: nowrap;
    }

    .story-copy {
      color: var(--muted-strong);
      line-height: 1.52;
      font-size: 0.9rem;
    }

    .story-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 9px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.04);
      color: var(--muted-strong);
      font-size: 0.74rem;
      border: 1px solid rgba(255, 255, 255, 0.06);
    }

    .module-actions,
    .story-actions,
    .detail-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }

    .mini-action,
    .story-action {
      padding: 9px 12px;
      border-radius: 999px;
      color: var(--muted-strong);
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.08);
      text-decoration: none;
    }

    .mini-action.primary,
    .story-action.primary {
      color: #e8fff5;
      background: rgba(118, 240, 191, 0.11);
      border-color: rgba(118, 240, 191, 0.24);
    }

    .detail-pane {
      position: sticky;
      top: 16px;
      display: grid;
      gap: 14px;
    }

    .detail-card {
      padding: 18px;
      display: grid;
      gap: 16px;
    }

    .detail-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
    }

    .detail-head h3 {
      font-size: 1.65rem;
      margin-bottom: 8px;
    }

    .detail-head p {
      margin: 0;
      color: var(--muted);
      line-height: 1.56;
    }

    .detail-section {
      padding-top: 2px;
      display: grid;
      gap: 10px;
    }

    .detail-section h4 {
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--muted);
      font-family: var(--font-body);
    }

    .detail-facts {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 8px;
    }

    .detail-facts li {
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      color: var(--muted-strong);
      line-height: 1.5;
    }

    .detail-facts strong {
      color: var(--text);
    }

    .detail-chart {
      margin-top: 4px;
    }

    .detail-links {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .api-index {
      margin-top: 18px;
      padding: 14px 16px;
    }

    .api-index summary {
      cursor: pointer;
      list-style: none;
      color: var(--muted-strong);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.72rem;
      font-weight: 700;
    }

    .api-index summary::-webkit-details-marker { display: none; }

    .api-grid {
      margin-top: 14px;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .api-link {
      display: grid;
      gap: 8px;
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid rgba(255, 255, 255, 0.06);
      text-decoration: none;
    }

    .api-link strong {
      font-size: 0.93rem;
      letter-spacing: -0.02em;
    }

    .api-link span {
      color: var(--muted);
      font-size: 0.84rem;
      line-height: 1.45;
    }

    .footer {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      flex-wrap: wrap;
      margin-top: 18px;
      color: var(--muted);
      font-size: 0.9rem;
    }

    .footer a {
      color: inherit;
      text-decoration: none;
      border-bottom: 1px solid rgba(255, 255, 255, 0.18);
    }

    .footer a:hover {
      color: var(--text);
      border-bottom-color: rgba(118, 240, 191, 0.5);
    }

    .loading-shell {
      display: grid;
      gap: 10px;
      margin-top: 14px;
    }

    .loading-line {
      height: 14px;
      border-radius: 999px;
      background: linear-gradient(90deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.05));
      background-size: 200% 100%;
      animation: shimmer 1.8s linear infinite;
    }

    .loading-line.short { width: 48%; }
    .loading-line.mid { width: 72%; }

    .pulse {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--accent);
      box-shadow: 0 0 0 0 rgba(118, 240, 191, 0.45);
      animation: pulse 1.6s infinite;
    }

    .empty-state {
      padding: 20px;
      border-radius: 20px;
      border: 1px dashed rgba(255, 255, 255, 0.14);
      color: var(--muted);
      line-height: 1.58;
      background: rgba(255, 255, 255, 0.02);
    }

    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(118, 240, 191, 0.42); }
      70% { box-shadow: 0 0 0 14px rgba(118, 240, 191, 0); }
      100% { box-shadow: 0 0 0 0 rgba(118, 240, 191, 0); }
    }

    @keyframes shimmer {
      0% { background-position: 0 50%; }
      100% { background-position: 200% 50%; }
    }

    @keyframes rise {
      from {
        opacity: 0;
        transform: translateY(12px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    @media (max-width: 1100px) {
      .hero,
      .content,
      .explore-bar {
        grid-template-columns: 1fr;
      }

      .detail-pane {
        position: static;
      }
    }

    @media (max-width: 760px) {
      .shell {
        padding: 16px 12px 24px;
      }

      .topbar {
        flex-direction: column;
        align-items: flex-start;
      }

      .nav {
        justify-content: flex-start;
      }

      .summary-grid,
      .module-grid,
      .metric-grid,
      .signal-grid,
      .api-grid {
        grid-template-columns: 1fr;
      }

      .hero-actions,
      .module-actions,
      .detail-actions,
      .story-actions {
        flex-direction: column;
        align-items: stretch;
      }

      .chart-bar {
        grid-template-columns: minmax(0, 1fr);
      }

      h1 {
        max-width: none;
        font-size: clamp(2.2rem, 14vw, 3.8rem);
      }
    }

    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        scroll-behavior: auto !important;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar" aria-label="Primary">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true"></span>
        md-data.org
      </div>
      <nav class="nav">
        <a href="/">Home</a>
        <a href="/docs">API Docs</a>
        <a href="/v1/search">Discovery</a>
        <a href="/status" aria-current="page">Status</a>
        <a href="/openapi.json">API</a>
      </nav>
    </header>

    <section class="hero" aria-label="Status overview">
      <div class="hero-copy">
        <div class="eyebrow">
          <span class="eyebrow-dot" aria-hidden="true"></span>
          data atlas · live exploration
        </div>
        <h1>Explore the data, not the endpoints.</h1>
        <p class="lede" id="hero-lede">
          The status page turns civic APIs into stories, charts, and cross-links so you can inspect procurement,
          EU funding, macro signals, and discovery without reading raw JSON first.
        </p>
        <div class="hero-actions">
          <button class="button primary" id="refresh-button" type="button">Refresh now</button>
          <label class="toggle" for="auto-refresh">
            <input id="auto-refresh" type="checkbox" checked>
            Auto refresh
          </label>
          <a class="button" href="/docs">Open docs</a>
          <a class="button" href="/v1/search">Jump to discovery</a>
        </div>
      </div>

      <div class="hero-rail">
        <section class="signal-card" aria-labelledby="signal-title">
          <div class="signal-top">
            <div>
              <div class="signal-title" id="signal-title">Current pulse</div>
              <div class="signal-name" id="overall-status">
                <span class="pulse" aria-hidden="true"></span>
                Loading atlas...
              </div>
            </div>
            <span class="section-state status-placeholder" id="overall-state">warming up</span>
          </div>
          <div class="signal-body" id="generated-meta">Waiting for live status payload.</div>
          <div class="signal-grid" id="hero-metrics"></div>
        </section>

        <section class="bridge-card" aria-labelledby="bridge-title">
          <div class="bridge-kicker">Cross-link spotlight</div>
          <div class="bridge-title" id="bridge-title">Loading bridge...</div>
          <div class="bridge-detail" id="bridge-detail">The procurement and EU funding thread will appear here once the payload loads.</div>
          <div class="bridge-row" id="bridge-actions"></div>
        </section>
      </div>
    </section>

    <section class="summary-panel" aria-label="Summary">
      <div class="summary-grid" id="summary-grid"></div>
    </section>

    <section class="explore-bar" aria-label="Explore filters">
      <label class="search-wrap" for="search-input">
        <span>Search across stories</span>
        <input id="search-input" type="search" placeholder="Try procurement, Cahul, EU, weather, rates, alerts..." autocomplete="off">
      </label>
      <div class="chip-row" id="filter-row" aria-label="Module filters"></div>
    </section>

    <div class="content">
      <section class="section-card" aria-labelledby="board-title">
        <div class="section-head">
          <div class="section-copy">
            <div class="section-kicker">Story board</div>
            <h2 id="board-title">Live modules, surfaced as stories</h2>
            <p>
              Each card turns a source API into something more usable: metrics, visual balance, linked records,
              and quick entry points to the underlying routes.
            </p>
          </div>
          <div class="section-state status-live" id="module-count">loading</div>
        </div>
        <div class="module-grid" id="module-grid">
          <div class="loading-shell" style="grid-column: 1 / -1;">
            <div class="loading-line mid"></div>
            <div class="loading-line short"></div>
            <div class="loading-line mid"></div>
          </div>
        </div>
      </section>

      <aside class="detail-pane" aria-label="Selected story">
        <article class="detail-card" id="detail-panel">
          <div class="loading-shell">
            <div class="loading-line mid"></div>
            <div class="loading-line short"></div>
            <div class="loading-line mid"></div>
          </div>
        </article>
      </aside>
    </div>

    <details class="api-index">
      <summary>Route index</summary>
      <div class="api-grid" id="api-grid"></div>
    </details>

    <footer class="footer">
      <span>Live page, JSON data endpoint, and curated source explorer from the FastAPI app.</span>
      <span><a href="/status/data">Open JSON payload</a></span>
    </footer>
  </div>

  <script>
    const state = {
      data: null,
      query: "",
      filter: "all",
      activeModuleId: null,
      activeStoryId: null,
      autoRefresh: true,
      refreshTimer: null
    };

    const stateStyles = {
      live: "status-live",
      ready: "status-ready",
      placeholder: "status-placeholder",
      degraded: "status-degraded"
    };

    const filterLabels = {
      all: "All",
      civic: "Civic",
      eu: "EU",
      macro: "Macro",
      discovery: "Discovery",
      linked: "Cross-linked"
    };

    const escapeHtml = (value) =>
      String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");

    const normalize = (value) => escapeHtml(value).toLowerCase();

    const formatDate = (value) => {
      if (!value) {
        return "Unknown";
      }
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        return String(value);
      }
      return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short"
      }).format(date);
    };

    const formatNumber = (value) =>
      new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(Number(value ?? 0));

    const formatMoney = (value, currency) => {
      const amount = Number(value ?? 0);
      const absAmount = Math.abs(amount);
      let display = amount;
      let suffix = "";

      if (absAmount >= 1_000_000_000) {
        display = amount / 1_000_000_000;
        suffix = "B";
      } else if (absAmount >= 1_000_000) {
        display = amount / 1_000_000;
        suffix = "M";
      } else if (absAmount >= 1_000) {
        display = amount / 1_000;
        suffix = "K";
      }

      const unit = currency ? ` ${currency}` : "";
      return suffix ? `${display.toFixed(1)}${suffix}${unit}` : `${formatNumber(display)}${unit}`;
    };

    const getVisibleModules = () => {
      const query = state.query.trim().toLowerCase();
      return (state.data?.sources || []).filter((module) => {
        if (state.filter !== "all" && state.filter !== "linked" && module.kind !== state.filter) {
          return false;
        }
        if (state.filter === "linked" && Number(module.cross_link_count || 0) <= 0) {
          return false;
        }
        if (!query) {
          return true;
        }
        const haystack = [
          module.name,
          module.kind,
          module.detail,
          module.note,
          ...(module.highlights || []),
          ...(module.metrics || []).map((metric) => `${metric.label} ${metric.value} ${metric.hint || ""}`),
          ...(module.stories || []).flatMap((story) => [
            story.title,
            story.meta,
            story.value,
            story.blurb,
            story.detail,
            story.route,
            story.route_label,
            ...(story.tags || [])
          ]),
          ...(module.routes || []).flatMap((route) => [route.label, route.href])
        ]
          .join(" ")
          .toLowerCase();
        return haystack.includes(query);
      });
    };

    const setStatusBadge = (element, stateName) => {
      const raw = String(stateName || "placeholder");
      const className = raw.startsWith("status-") ? raw : (stateStyles[raw] || stateStyles.placeholder);
      element.className = `section-state ${className}`;
      element.textContent = raw.replace(/^status-/, "");
    };

    const renderSummary = () => {
      const summaryGrid = document.getElementById("summary-grid");
      const items = state.data?.summary || [];
      summaryGrid.innerHTML = items.map((item) => `
        <article class="summary-card">
          <div class="summary-value">${escapeHtml(item.value)}</div>
          <div class="summary-label">${escapeHtml(item.label)}</div>
        </article>
      `).join("");
    };

    const renderHero = () => {
      const heroMetrics = document.getElementById("hero-metrics");
      const metrics = state.data?.hero_metrics || [];
      heroMetrics.innerHTML = metrics.map((item) => `
        <div class="signal-stat">
          <strong>${escapeHtml(item.value)}</strong>
          <span>${escapeHtml(item.label)}</span>
        </div>
      `).join("");

      const bridge = state.data?.bridge || {};
      document.getElementById("bridge-title").textContent = bridge.title || "Cross-link spotlight";
      document.getElementById("bridge-detail").textContent = bridge.detail || "No bridge data available.";
      const actions = document.getElementById("bridge-actions");
      const buttons = [];
      if (bridge.project?.route) {
        buttons.push(`<a class="bridge-pill" href="${escapeHtml(bridge.project.route)}">${escapeHtml(bridge.project.title || "Open project")}</a>`);
      }
      if (bridge.tender?.route) {
        buttons.push(`<a class="bridge-pill" href="${escapeHtml(bridge.tender.route)}">${escapeHtml(bridge.tender.title || "Open tender")}</a>`);
      }
      if (!buttons.length) {
        buttons.push(`<span class="bridge-pill">Bridge will appear when links are present</span>`);
      }
      actions.innerHTML = buttons.join("");
    };

    const renderModuleTabs = () => {
      const filterRow = document.getElementById("filter-row");
      const chips = Object.entries(filterLabels).map(([key, label]) => `
        <button
          class="chip${state.filter === key ? " active" : ""}"
          type="button"
          data-action="set-filter"
          data-filter="${escapeHtml(key)}"
          aria-pressed="${state.filter === key ? "true" : "false"}"
        >${escapeHtml(label)}</button>
      `);
      filterRow.innerHTML = chips.join("");
    };

    const renderApiIndex = () => {
      const grid = document.getElementById("api-grid");
      const modules = state.data?.sources || [];
      grid.innerHTML = modules.flatMap((module) => (module.routes || []).map((route) => `
        <a class="api-link" href="${escapeHtml(route.href)}">
          <strong>${escapeHtml(route.label)}</strong>
          <span>${escapeHtml(module.name)} · ${escapeHtml(route.href)}</span>
        </a>
      `)).join("");
    };

    const renderDetail = (module) => {
      const detail = document.getElementById("detail-panel");
      if (!module) {
        detail.innerHTML = `
          <div class="empty-state">
            No module selected. Use the search box or the filter chips to focus the explorer.
          </div>
        `;
        return;
      }

      const selectedStory = (module.stories || []).find((story) => story.id === state.activeStoryId) || module.stories?.[0] || null;
      const storyPoints = selectedStory?.points || [];
      const moduleMetrics = module.metrics || [];
      const moduleChart = module.chart || [];

      detail.innerHTML = `
        <div class="detail-head">
          <div>
            <div class="section-kicker">${escapeHtml(module.kicker || module.kind || "module")}</div>
            <h3>${escapeHtml(module.name)}</h3>
            <p>${escapeHtml(module.detail || "")}</p>
          </div>
          <div class="section-state ${stateStyles[module.state] || stateStyles.placeholder}">${escapeHtml(module.state || "ready")}</div>
        </div>

        <div class="module-actions">
          ${(module.routes || []).map((route) => `
            <a class="mini-action" href="${escapeHtml(route.href)}">${escapeHtml(route.label)}</a>
          `).join("")}
        </div>

        <div class="metric-grid">
          ${moduleMetrics.map((metric) => `
            <div class="metric">
              <strong>${escapeHtml(metric.value)}</strong>
              <span>${escapeHtml(metric.label)}${metric.hint ? ` · ${escapeHtml(metric.hint)}` : ""}</span>
            </div>
          `).join("")}
        </div>

        <div class="detail-section">
          <h4>Highlights</h4>
          <ul class="highlights">
            ${(module.highlights || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
          </ul>
        </div>

        <div class="detail-section">
          <h4>Selected story</h4>
          ${selectedStory ? `
            <article class="story-card is-active" style="cursor: default;">
              <div class="story-top">
                <div>
                  <div class="story-kicker">${escapeHtml(selectedStory.kicker)}</div>
                  <div class="story-title">${escapeHtml(selectedStory.title)}</div>
                  <div class="story-meta">${escapeHtml(selectedStory.meta)}</div>
                </div>
                <div class="story-value">${escapeHtml(selectedStory.value)}</div>
              </div>
              <div class="story-copy">${escapeHtml(selectedStory.blurb)}</div>
              <div class="story-copy">${escapeHtml(selectedStory.detail)}</div>
              <div class="story-tags">
                ${(selectedStory.tags || []).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}
              </div>
              <div class="detail-actions">
                <a class="story-action primary" href="${escapeHtml(selectedStory.route)}">${escapeHtml(selectedStory.route_label)}</a>
                ${selectedStory.secondary_route ? `<a class="story-action" href="${escapeHtml(selectedStory.secondary_route)}">${escapeHtml(selectedStory.secondary_label || "Open link")}</a>` : ""}
                <button class="story-action" type="button" data-action="copy-route" data-copy="${escapeHtml(selectedStory.route)}">Copy route</button>
              </div>
            </article>
          ` : `
            <div class="empty-state">This module does not have a selected story yet.</div>
          `}
        </div>

        <div class="detail-section detail-chart">
          <h4>Visual balance</h4>
          <div class="chart">
            ${moduleChart.map((item) => `
              <div class="chart-bar">
                <div class="chart-label">${escapeHtml(item.label)}</div>
                <div class="chart-track">
                  <div class="chart-fill" style="width:${escapeHtml(item.width)}%;"></div>
                </div>
                <div class="chart-value">${escapeHtml(item.display)}</div>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    };

    const renderModules = () => {
      const visible = getVisibleModules();
      const grid = document.getElementById("module-grid");
      const count = document.getElementById("module-count");
      count.textContent = `${visible.length} module${visible.length === 1 ? "" : "s"} visible`;

      if (!visible.length) {
        grid.innerHTML = `
          <div class="empty-state" style="grid-column: 1 / -1;">
            No modules matched your search. Try a different query or reset the filter chips.
          </div>
        `;
        renderDetail(null);
        return;
      }

      if (!state.activeModuleId || !visible.some((module) => module.id === state.activeModuleId)) {
        state.activeModuleId = visible[0].id;
        state.activeStoryId = visible[0].stories?.[0]?.id || null;
      }

      const selectedModule = visible.find((module) => module.id === state.activeModuleId) || visible[0];
      if (selectedModule && !selectedModule.stories?.some((story) => story.id === state.activeStoryId)) {
        state.activeStoryId = selectedModule.stories?.[0]?.id || null;
      }

      grid.innerHTML = visible.map((module, index) => {
        const isActive = module.id === selectedModule?.id;
        const previewStories = (module.stories || []).slice(0, 3);
        return `
          <article class="module-card${isActive ? " is-active" : ""}" style="--accent:${escapeHtml(module.accent || "#85a8ff")}; animation-delay:${index * 70}ms;">
            <div class="module-head">
              <div>
                <div class="module-kicker">${escapeHtml(module.kicker || module.kind || "")}</div>
                <h3>${escapeHtml(module.name)}</h3>
                <p class="module-detail">${escapeHtml(module.detail || "")}</p>
              </div>
              <div class="section-state ${stateStyles[module.state] || stateStyles.placeholder}">${escapeHtml(module.state || "ready")}</div>
            </div>

            <div class="metric-grid">
              ${(module.metrics || []).map((metric) => `
                <div class="metric">
                  <strong>${escapeHtml(metric.value)}</strong>
                  <span>${escapeHtml(metric.label)}${metric.hint ? ` · ${escapeHtml(metric.hint)}` : ""}</span>
                </div>
              `).join("")}
            </div>

            <ul class="highlights">
              ${(module.highlights || []).slice(0, 3).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
            </ul>

            <div class="chart">
              ${(module.chart || []).slice(0, 3).map((item) => `
                <div class="chart-bar">
                  <div class="chart-label">${escapeHtml(item.label)}</div>
                  <div class="chart-track">
                    <div class="chart-fill" style="width:${escapeHtml(item.width)}%;"></div>
                  </div>
                  <div class="chart-value">${escapeHtml(item.display)}</div>
                </div>
              `).join("")}
            </div>

            <div class="story-list">
              ${previewStories.map((story) => `
                <button class="story-card${story.id === state.activeStoryId ? " is-active" : ""}" type="button" data-action="select-story" data-module-id="${escapeHtml(module.id)}" data-story-id="${escapeHtml(story.id)}">
                  <div class="story-top">
                    <div>
                      <div class="story-kicker">${escapeHtml(story.kicker)}</div>
                      <div class="story-title">${escapeHtml(story.title)}</div>
                      <div class="story-meta">${escapeHtml(story.meta)}</div>
                    </div>
                    <div class="story-value">${escapeHtml(story.value)}</div>
                  </div>
                  <div class="story-copy">${escapeHtml(story.blurb)}</div>
                </button>
              `).join("")}
            </div>

            <div class="module-actions">
              <button class="mini-action primary" type="button" data-action="select-module" data-module-id="${escapeHtml(module.id)}">Explore module</button>
              ${(module.routes || []).slice(0, 3).map((route) => `
                <a class="mini-action" href="${escapeHtml(route.href)}">${escapeHtml(route.label)}</a>
              `).join("")}
            </div>
          </article>
        `;
      }).join("");

      renderDetail(selectedModule);
    };

    const renderAll = () => {
      if (!state.data) {
        return;
      }
      const overall = state.data.overall || {};
      const overallStatus = document.getElementById("overall-status");
      const overallState = document.getElementById("overall-state");
      overallStatus.innerHTML = `<span class="pulse" aria-hidden="true"></span> ${escapeHtml(overall.label || "operational")}`;
      setStatusBadge(overallState, overall.class_name || "live");
      document.getElementById("generated-meta").textContent =
        `Updated ${formatDate(state.data.generated_at)} · ${state.data.summary?.[0]?.value || 0} modules · ${state.data.summary?.[1]?.value || 0} stories`;
      document.getElementById("hero-lede").textContent = state.data.hero?.lede || document.getElementById("hero-lede").textContent;
      renderHero();
      renderSummary();
      renderModuleTabs();
      renderModules();
      renderApiIndex();
      document.getElementById("module-count").textContent = `${getVisibleModules().length} module${getVisibleModules().length === 1 ? "" : "s"} visible`;
    };

    const hydrate = async () => {
      try {
        document.getElementById("refresh-button").textContent = "Refreshing...";
        const response = await fetch("/status/data", { headers: { accept: "application/json" } });
        if (!response.ok) {
          throw new Error(`Status payload returned ${response.status}`);
        }
        state.data = await response.json();
        const overall = state.data.overall || {};
        setStatusBadge(document.getElementById("overall-state"), overall.class_name || "live");
        renderAll();
      } catch (error) {
        console.error(error);
        document.getElementById("overall-status").innerHTML = `<span class="pulse" aria-hidden="true"></span> degraded`;
        document.getElementById("overall-state").className = "section-state status-degraded";
        document.getElementById("overall-state").textContent = "degraded";
        document.getElementById("generated-meta").textContent = "The status payload could not be loaded. Check the API process or upstream source health.";
        document.getElementById("summary-grid").innerHTML = "";
        document.getElementById("hero-metrics").innerHTML = "";
        document.getElementById("bridge-title").textContent = "Status payload unavailable";
        document.getElementById("bridge-detail").textContent = error.message || "Unknown error";
        document.getElementById("bridge-actions").innerHTML = `<span class="bridge-pill">Retry after checking the API process</span>`;
        document.getElementById("module-grid").innerHTML = `
          <div class="empty-state" style="grid-column: 1 / -1;">
            The explorer could not load its payload. Refresh after confirming the API is running.
          </div>
        `;
        document.getElementById("detail-panel").innerHTML = `
          <div class="empty-state">No detail view is available because the payload failed to load.</div>
        `;
      } finally {
        document.getElementById("refresh-button").textContent = "Refresh now";
      }
    };

    const bindEvents = () => {
      document.getElementById("refresh-button").addEventListener("click", () => hydrate());

      document.getElementById("auto-refresh").addEventListener("change", (event) => {
        state.autoRefresh = event.target.checked;
        if (state.refreshTimer) {
          clearInterval(state.refreshTimer);
          state.refreshTimer = null;
        }
        if (state.autoRefresh) {
          state.refreshTimer = setInterval(() => {
            hydrate();
          }, 120000);
        }
      });

      document.getElementById("search-input").addEventListener("input", (event) => {
        state.query = event.target.value;
        renderModules();
      });

      document.getElementById("filter-row").addEventListener("click", (event) => {
        const button = event.target.closest("[data-action='set-filter']");
        if (!button) {
          return;
        }
        state.filter = button.dataset.filter || "all";
        renderModuleTabs();
        renderModules();
      });

      document.getElementById("module-grid").addEventListener("click", (event) => {
        const moduleButton = event.target.closest("[data-action='select-module']");
        if (moduleButton) {
          state.activeModuleId = moduleButton.dataset.moduleId;
          const module = (state.data?.sources || []).find((item) => item.id === state.activeModuleId);
          state.activeStoryId = module?.stories?.[0]?.id || null;
          renderModules();
          return;
        }

        const storyButton = event.target.closest("[data-action='select-story']");
        if (storyButton) {
          state.activeModuleId = storyButton.dataset.moduleId;
          state.activeStoryId = storyButton.dataset.storyId;
          renderModules();
        }
      });

      document.getElementById("detail-panel").addEventListener("click", async (event) => {
        const copyButton = event.target.closest("[data-action='copy-route']");
        if (!copyButton) {
          return;
        }
        const text = copyButton.dataset.copy || "";
        try {
          await navigator.clipboard.writeText(text);
          copyButton.textContent = "Copied";
          setTimeout(() => {
            copyButton.textContent = "Copy route";
          }, 1200);
        } catch (error) {
          console.error(error);
        }
      });
    };

    bindEvents();
    hydrate();
    if (state.autoRefresh) {
      state.refreshTimer = setInterval(() => {
        hydrate();
      }, 120000);
    }
  </script>
</body>
</html>
"""


def _build_procurement_module(
    tenders: list[dict[str, Any]],
    awards: list[dict[str, Any]],
    contracts: list[dict[str, Any]],
    budgets: list[dict[str, Any]],
    plans: list[dict[str, Any]],
    stats: dict[str, Any],
) -> dict[str, Any]:
    by_raion = stats.get("by_raion", {}) or {}
    raion_chart = []
    raion_values = [float((amount or {}).get("amount", 0.0) or 0.0) for amount in by_raion.values()]
    max_raion = max(raion_values) if raion_values else 0.0
    for raion, amount in list(by_raion.items())[:4]:
        amount_value = float((amount or {}).get("amount", 0.0) or 0.0)
        raion_chart.append(
            {
                "label": raion,
                "value": amount_value,
                "display": _format_amount(amount_value, (amount or {}).get("currency", "MDL")),
                "width": round((amount_value / max_raion) * 100) if max_raion else 0,
            }
        )

    ordered_tenders = sorted(tenders, key=lambda item: float((item.get("value") or {}).get("amount", 0.0) or 0.0), reverse=True)
    linked_project_ids = sorted({project_id for tender in tenders for project_id in (tender.get("cross_references") or {}).get("eu_project_ids", [])})

    stories: list[dict[str, Any]] = []
    if ordered_tenders:
        tender = ordered_tenders[0]
        value = tender.get("value") or {}
        location = tender.get("location") or {}
        buyer = tender.get("buyer") or {}
        project_ids = (tender.get("cross_references") or {}).get("eu_project_ids", [])
        stories.append(
            _make_story(
                story_id=tender["ocid"],
                kicker="Tender",
                title=tender["title"],
                meta=f"{location.get('raion') or 'Unknown raion'} · {buyer.get('sector') or 'General'} · {tender.get('status') or 'unknown'}",
                value=_format_amount(value.get("amount"), value.get("currency", "MDL")),
                blurb=tender.get("description") or "OCDS-normalized tender record with location and buyer context.",
                detail=f"Buyer: {buyer.get('name') or 'Unknown buyer'} · Cross-links: {len(project_ids)} EU project id(s).",
                route=f"/v1/procurement/tenders/{tender['ocid']}",
                route_label="Open tender",
                secondary_route=f"/v1/eu-funds/projects/{project_ids[0]}" if project_ids else None,
                secondary_label="Open EU project" if project_ids else None,
                tags=[location.get("raion") or "Unknown", buyer.get("sector") or "Unclassified", "OCDS"],
                tone="live",
            )
        )

    if awards:
        award = awards[0]
        stories.append(
            _make_story(
                story_id=award["ocid"],
                kicker="Award",
                title=award["title"],
                meta=f"{award.get('raion') or 'Unknown raion'} · {award.get('status') or 'unknown'}",
                value=_format_amount((award.get("value") or {}).get("amount"), (award.get("value") or {}).get("currency", "MDL")),
                blurb=award.get("supplier_name") or "Supplier information not yet surfaced.",
                detail=f"Tender OCID: {award.get('tender_ocid') or 'n/a'} · Supplier: {award.get('supplier_name') or 'Unknown'}",
                route="/v1/procurement/awards",
                route_label="Open awards",
                tags=[award.get("raion") or "Unknown", "Award"],
                tone="ready",
            )
        )

    if contracts:
        contract = contracts[0]
        stories.append(
            _make_story(
                story_id=contract["ocid"],
                kicker="Contract",
                title=contract["title"],
                meta=f"{contract.get('raion') or 'Unknown raion'} · signed",
                value=_format_amount((contract.get("value") or {}).get("amount"), (contract.get("value") or {}).get("currency", "MDL")),
                blurb=contract.get("supplier_name") or "Contract supplier context not surfaced.",
                detail=f"Award OCID: {contract.get('award_ocid') or 'n/a'} · Signed: {_format_datetime(contract.get('signed_at'))}",
                route="/v1/procurement/contracts",
                route_label="Open contracts",
                tags=[contract.get("raion") or "Unknown", "Contract"],
                tone="ready",
            )
        )

    if budgets:
        budget = budgets[0]
        stories.append(
            _make_story(
                story_id=budget["code"],
                kicker="Budget",
                title=budget["name"],
                meta=f"{budget.get('raion') or 'Unknown raion'} · {budget.get('status') or 'planning'}",
                value=_format_amount((budget.get("amount") or {}).get("amount"), (budget.get("amount") or {}).get("currency", "MDL")),
                blurb=budget.get("description") or "Budget planning view for procurement demand.",
                detail=f"Entity: {budget.get('buyer_name') or 'Unknown buyer'} · Sector: {budget.get('buyer_sector') or 'General'}",
                route="/v1/procurement/budgets",
                route_label="Open budgets",
                tags=[budget.get("raion") or "Unknown", "Budget"],
                tone="ready",
            )
        )

    if plans:
        plan = plans[0]
        stories.append(
            _make_story(
                story_id=plan["ocid"],
                kicker="Plan",
                title=plan["title"],
                meta=f"{plan.get('raion') or 'Unknown raion'} · {plan.get('status') or 'published'}",
                value=f"{len(plan.get('related_tender_ocids') or [])} related tender(s)",
                blurb="Planning layer for upcoming procurement activity.",
                detail=f"Buyer: {plan.get('buyer_name') or 'Unknown buyer'} · Sector: {plan.get('buyer_sector') or 'General'}",
                route="/v1/procurement/plans",
                route_label="Open plans",
                tags=[plan.get("raion") or "Unknown", "Plan"],
                tone="ready",
            )
        )

    if not stories:
        stories.append(
            _make_story(
                story_id="procurement-empty",
                kicker="Tender",
                title="No procurement records yet",
                meta="Waiting for sync",
                value="—",
                blurb="The procurement module will populate when the MTender sync has records.",
                detail="Use the endpoint routes to inspect live MTender data directly.",
                route="/v1/procurement/tenders",
                route_label="Open tenders",
                tags=["Placeholder"],
                tone="placeholder",
            )
        )

    total_budget = stats.get("total_budget") or {}
    cross_links = len(linked_project_ids)
    sector_labels = stats.get("top_sectors") or ["General"]
    highlights = [
        f"{stats.get('total_tenders', 0)} tenders, {stats.get('total_awards', 0)} awards, {stats.get('total_contracts', 0)} contracts, {len(budgets)} budgets, and {len(plans)} plans are staged together.",
        f"{cross_links} EU project id(s) are linked to procurement records.",
        f"{sector_labels[0]} leads the current sector mix." + (f" {sector_labels[1]} follows closely." if len(sector_labels) > 1 else ""),
    ]

    return {
        "id": "procurement",
        "kind": "civic",
        "kicker": "MTender / OCDS",
        "name": "Civic procurement",
        "state": "live" if tenders else "placeholder",
        "detail": f"{len(tenders)} tenders, {len(awards)} awards, {len(contracts)} contracts, {len(budgets)} budgets, and {len(plans)} plans. The view is raion-aware and cross-linked to EU funding.",
        "note": "OCDS-normalized procurement with raion filtering and link stitching.",
        "accent": "#f7bf65",
        "cross_link_count": cross_links,
        "metrics": [
            {"label": "Tenders", "value": str(len(tenders)), "hint": "live records"},
            {"label": "Awards", "value": str(len(awards)), "hint": "linked procurement"},
            {"label": "Contracts", "value": str(len(contracts)), "hint": "signed records"},
            {"label": "Budget", "value": _format_amount((total_budget or {}).get("amount"), (total_budget or {}).get("currency", "MDL")), "hint": "planning layer"},
        ],
        "highlights": highlights,
        "chart": raion_chart,
        "stories": stories,
        "routes": [
            {"label": "Tenders", "href": "/v1/procurement/tenders"},
            {"label": "Awards", "href": "/v1/procurement/awards"},
            {"label": "Contracts", "href": "/v1/procurement/contracts"},
            {"label": "Budgets", "href": "/v1/procurement/budgets"},
            {"label": "Plans", "href": "/v1/procurement/plans"},
            {"label": "Statistics", "href": "/v1/procurement/statistics"},
        ],
    }


def _build_eu_module(projects: list[dict[str, Any]], stats: dict[str, Any]) -> dict[str, Any]:
    sector_map = stats.get("by_sector", {}) or {}
    sector_values = [float((amount or {}).get("amount", 0.0) or 0.0) for amount in sector_map.values()]
    max_sector = max(sector_values) if sector_values else 0.0
    sector_chart = []
    for sector, amount in list(sector_map.items())[:4]:
        amount_value = float((amount or {}).get("amount", 0.0) or 0.0)
        sector_chart.append(
            {
                "label": sector,
                "value": amount_value,
                "display": _format_amount(amount_value, (amount or {}).get("currency", "EUR")),
                "width": round((amount_value / max_sector) * 100) if max_sector else 0,
            }
        )

    raion_map = stats.get("by_raion", {}) or {}
    raion_values = [float((amount or {}).get("amount", 0.0) or 0.0) for amount in raion_map.values()]
    max_raion = max(raion_values) if raion_values else 0.0
    raion_chart = []
    for raion, amount in list(raion_map.items())[:4]:
        amount_value = float((amount or {}).get("amount", 0.0) or 0.0)
        raion_chart.append(
            {
                "label": raion,
                "value": amount_value,
                "display": _format_amount(amount_value, (amount or {}).get("currency", "EUR")),
                "width": round((amount_value / max_raion) * 100) if max_raion else 0,
            }
        )

    ordered_projects = sorted(projects, key=lambda item: float((item.get("funding_amount") or {}).get("amount", 0.0) or 0.0), reverse=True)
    linked_tender_ids = sorted({ocid for project in projects for ocid in project.get("linked_procurement_ocids", [])})

    stories: list[dict[str, Any]] = []
    if ordered_projects:
        project = ordered_projects[0]
        funding = project.get("funding_amount") or {}
        location = project.get("location") or {}
        stories.append(
            _make_story(
                story_id=project["id"],
                kicker="Project",
                title=project["title"],
                meta=f"{project.get('status') or 'ongoing'} · {location.get('raion') or project.get('sector') or 'Unknown raion'}",
                value=_format_amount(funding.get("amount"), funding.get("currency", "EUR")),
                blurb=project.get("description") or "EU-funded project with location and beneficiary context.",
                detail=f"Beneficiary: {project.get('beneficiary') or 'Unknown'} · Linked tenders: {len(project.get('linked_procurement_ocids') or [])}",
                route=f"/v1/eu-funds/projects/{project['id']}",
                route_label="Open project",
                secondary_route=f"/v1/procurement/tenders/{project['linked_procurement_ocids'][0]}" if project.get("linked_procurement_ocids") else None,
                secondary_label="Open tender" if project.get("linked_procurement_ocids") else None,
                tags=[location.get("raion") or "Unknown", project.get("sector") or "General", "EU4Moldova"],
                tone="live",
            )
        )

    if len(ordered_projects) > 1:
        project = ordered_projects[1]
        funding = project.get("funding_amount") or {}
        location = project.get("location") or {}
        stories.append(
            _make_story(
                story_id=f"{project['id']}-secondary",
                kicker="Project",
                title=project["title"],
                meta=f"{project.get('status') or 'ongoing'} · {location.get('raion') or project.get('sector') or 'Unknown raion'}",
                value=_format_amount(funding.get("amount"), funding.get("currency", "EUR")),
                blurb=project.get("description") or "Secondary EU project in the funding set.",
                detail=f"Beneficiary: {project.get('beneficiary') or 'Unknown'}",
                route=f"/v1/eu-funds/projects/{project['id']}",
                route_label="Open project",
                tags=[location.get("raion") or "Unknown", project.get("sector") or "General"],
                tone="ready",
            )
        )

    if stats:
        stories.append(
            _make_story(
                story_id="eu-funding-statistics",
                kicker="Statistics",
                title="Funding distribution",
                meta=f"{stats.get('total_projects', 0)} project(s) · {len(linked_tender_ids)} linked tender(s)",
                value=_format_amount((stats.get("total_funding") or {}).get("amount"), (stats.get("total_funding") or {}).get("currency", "EUR")),
                blurb="Sector and raion balance across the current EU project sample.",
                detail="Use the route index to inspect the project list and funding totals.",
                route="/v1/eu-funds/statistics",
                route_label="Open statistics",
                tags=["Funding", "Distribution"],
                tone="ready",
            )
        )

    if not stories:
        stories.append(
            _make_story(
                story_id="eu-funding-empty",
                kicker="Project",
                title="No EU projects yet",
                meta="Waiting for sync",
                value="—",
                blurb="The EU funding module will populate once the scraper or database has records.",
                detail="Open the project route to inspect the live endpoint when data is available.",
                route="/v1/eu-funds/projects",
                route_label="Open projects",
                tags=["Placeholder"],
                tone="placeholder",
            )
        )

    total_funding = stats.get("total_funding") or {}
    highlights = [
        f"{stats.get('total_projects', 0)} project(s) carry {_format_amount((total_funding or {}).get('amount'), (total_funding or {}).get('currency', 'EUR'))} in funding.",
        f"{len(linked_tender_ids)} procurement tender(s) are linked across the EU project set.",
        f"{next(iter(sector_map.keys()), 'General')} leads the visible sector mix.",
    ]

    return {
        "id": "eu-funds",
        "kind": "eu",
        "kicker": "EU4Moldova / Growth Plan",
        "name": "EU funding",
        "state": "live" if projects else "placeholder",
        "detail": f"{stats.get('total_projects', 0)} projects and {len(linked_tender_ids)} linked procurement tender(s). The view is normalized by raion and sector.",
        "note": "EU projects are normalized, searchable, and cross-linked to procurement.",
        "accent": "#76f0bf",
        "cross_link_count": len(linked_tender_ids),
        "metrics": [
            {"label": "Projects", "value": str(stats.get("total_projects", 0)), "hint": "live records"},
            {"label": "Funding", "value": _format_amount((total_funding or {}).get("amount"), (total_funding or {}).get("currency", "EUR")), "hint": "project total"},
            {"label": "Sectors", "value": str(len(sector_map)), "hint": "distribution"},
            {"label": "Linked tenders", "value": str(len(linked_tender_ids)), "hint": "cross-reference"},
        ],
        "highlights": highlights,
        "chart": sector_chart or raion_chart,
        "stories": stories,
        "routes": [
            {"label": "Projects", "href": "/v1/eu-funds/projects"},
            {"label": "Statistics", "href": "/v1/eu-funds/statistics"},
        ],
    }


def _build_macro_module(
    finance_snapshot: dict[str, Any],
    weather_snapshot: dict[str, Any],
    alerts: list[dict[str, Any]],
    stats: list[dict[str, Any]],
) -> dict[str, Any]:
    rates = finance_snapshot.get("rates", []) or []
    rate_values = [float(rate.get("value", 0.0) or 0.0) for rate in rates]
    max_rate = max(rate_values) if rate_values else 0.0
    rate_chart = []
    for rate in rates[:4]:
        value = float(rate.get("value", 0.0) or 0.0)
        rate_chart.append(
            {
                "label": rate.get("currency", "FX"),
                "value": value,
                "display": f"{_format_decimal(value)} MDL",
                "width": round((value / max_rate) * 100) if max_rate else 0,
            }
        )

    weather_location = weather_snapshot.get("location") or {}
    weather_city = weather_location.get("city") or weather_location.get("raion") or "Chisinau"
    alert = alerts[0] if alerts else {}
    stat_item = stats[0] if stats else {}

    stories = [
        _make_story(
            story_id="fx-feed",
            kicker="FX",
            title="BNM exchange rates",
            meta=f"{finance_snapshot.get('date') or 'today'} · {finance_snapshot.get('source_status') or 'unknown'}",
            value=f"{len(rates)} rate(s)",
            blurb=f"Base currency: {finance_snapshot.get('base') or 'MDL'}",
            detail=f"Source: {finance_snapshot.get('source') or 'n/a'}",
            route="/v1/finance/exchange-rates",
            route_label="Open rates",
            tags=["BNM", finance_snapshot.get("base") or "MDL"],
            tone="live" if finance_snapshot.get("source_status") == "live" else "ready",
        ),
        _make_story(
            story_id="weather-feed",
            kicker="Weather",
            title=f"{weather_city} weather",
            meta=f"{weather_snapshot.get('condition') or 'clear'} · {weather_city}",
            value=f"{weather_snapshot.get('temperature') or '—'}°C",
            blurb="Current weather signal for the capital and its surrounding raion.",
            detail=f"Last updated: {_format_datetime(weather_snapshot.get('last_updated'))}",
            route="/v1/weather/current",
            route_label="Open weather",
            tags=[weather_city, weather_snapshot.get("condition") or "clear"],
            tone="ready",
        ),
        _make_story(
            story_id="alert-feed",
            kicker="Alerts",
            title=alert.get("title") or "Emergency alerts",
            meta=f"{alert.get('region') or 'Moldova'} · {alert.get('severity') or 'info'}",
            value=f"{len(alerts)} alert(s)",
            blurb=alert.get("description") or "Emergency feed ready for the IGSU integration.",
            detail=f"Source: {alert.get('source_url') or 'n/a'}",
            route="/v1/emergencies/alerts",
            route_label="Open alerts",
            tags=[alert.get("region") or "Moldova", alert.get("severity") or "info"],
            tone="placeholder" if not alerts else "ready",
        ),
        _make_story(
            story_id="stats-feed",
            kicker="Statistics",
            title=stat_item.get("indicator") or "Official statistics",
            meta=stat_item.get("source_url") or "NBS Statbank PxWeb",
            value=stat_item.get("value") or "NBS Statbank PxWeb",
            blurb="The official statistics summary anchors the discovery layer.",
            detail=f"Unit: {stat_item.get('unit') or 'n/a'}",
            route="/v1/statistics/summary",
            route_label="Open summary",
            tags=["NBS", "Discovery"],
            tone="ready",
        ),
    ]

    highlights = [
        f"{len(rates)} exchange rate(s) are live from the BNM feed.",
        f"{len(alerts)} emergency alert(s) are currently visible.",
        f"{weather_city} is the active weather lens in this snapshot.",
    ]

    return {
        "id": "macro",
        "kind": "macro",
        "kicker": "BNM / Meteo / IGSU / NBS",
        "name": "Macro signals",
        "state": "live" if finance_snapshot.get("source_status") == "live" else "ready",
        "detail": f"{len(rates)} exchange rates, a live weather reading, emergency alerts, and the official statistics source.",
        "note": "Macro context keeps the rest of the atlas grounded.",
        "accent": "#85a8ff",
        "cross_link_count": 0,
        "metrics": [
            {"label": "Rates", "value": str(len(rates)), "hint": finance_snapshot.get("base") or "MDL"},
            {"label": "Temp", "value": f"{weather_snapshot.get('temperature') or '—'}°C", "hint": weather_city},
            {"label": "Alerts", "value": str(len(alerts)), "hint": "feed state"},
            {"label": "Stats", "value": stat_item.get("value") or "n/a", "hint": "source anchor"},
        ],
        "highlights": highlights,
        "chart": rate_chart,
        "stories": stories,
        "routes": [
            {"label": "Exchange rates", "href": "/v1/finance/exchange-rates"},
            {"label": "Weather", "href": "/v1/weather/current"},
            {"label": "Alerts", "href": "/v1/emergencies/alerts"},
            {"label": "Summary", "href": "/v1/statistics/summary"},
        ],
    }


def _build_discovery_module(catalog: list[dict[str, Any]]) -> dict[str, Any]:
    source_counts = Counter(item.get("source") or "Unknown" for item in catalog)
    max_count = max(source_counts.values()) if source_counts else 0
    chart = [
        {
            "label": label,
            "value": count,
            "display": f"{count} route(s)",
            "width": round((count / max_count) * 100) if max_count else 0,
        }
        for label, count in source_counts.items()
    ]

    stories = [
        _make_story(
            story_id=f"catalog-{index}",
            kicker="Search result",
            title=item.get("title") or "Untitled",
            meta=item.get("source") or "Unknown source",
            value=item.get("url") or "—",
            blurb=item.get("description") or "",
            detail="Open this route to jump directly into the underlying data source.",
            route=item.get("url") or "/v1/search",
            route_label="Open source",
            tags=[item.get("source") or "Unknown"],
            tone="ready",
        )
        for index, item in enumerate(catalog[:4], start=1)
    ]

    if not stories:
        stories.append(
            _make_story(
                story_id="catalog-empty",
                kicker="Search result",
                title="No search results yet",
                meta="Discovery index",
                value="—",
                blurb="The search index will surface source entries as soon as the catalog is populated.",
                detail="Use the discovery route to inspect the live source registry.",
                route="/v1/search",
                route_label="Open discovery",
                tags=["Placeholder"],
                tone="placeholder",
            )
        )

    highlights = [
        f"{len(catalog)} catalog entry(ies) are exposed through discovery.",
        "Search is the quickest way to jump between the modules in this atlas.",
        "Use the route index below if you want the raw API entry points.",
    ]

    return {
        "id": "discovery",
        "kind": "discovery",
        "kicker": "Search index",
        "name": "Discovery",
        "state": "ready",
        "detail": "Discovery turns the source registry into a searchable directory rather than a raw endpoint list.",
        "note": "A compact jump table for all exposed data routes.",
        "accent": "#f49ac2",
        "cross_link_count": 0,
        "metrics": [
            {"label": "Catalog items", "value": str(len(catalog)), "hint": "searchable"},
            {"label": "Sources", "value": str(len(source_counts)), "hint": "families"},
            {"label": "Routes", "value": str(sum(source_counts.values())), "hint": "jump points"},
            {"label": "Query", "value": "ready", "hint": "free text"},
        ],
        "highlights": highlights,
        "chart": chart,
        "stories": stories,
        "routes": [
            {"label": "Discovery", "href": "/v1/search"},
        ],
    }


async def build_status_payload() -> dict[str, object]:
    finance_snapshot, weather_snapshot, alerts, tenders, awards, contracts, budgets, plans, procurement_stats, projects, eu_stats, stats, catalog = await asyncio.gather(
        _safe_call("finance", get_exchange_rates(), {}),
        _safe_call("weather", get_current_weather(), {}),
        _safe_call("alerts", get_emergency_alerts(), []),
        _safe_call("tenders", list_tenders(raion=None, status=None, query=None), []),
        _safe_call("awards", list_awards(raion=None), []),
        _safe_call("contracts", list_contracts(raion=None), []),
        _safe_call("budgets", list_budgets(raion=None), []),
        _safe_call("plans", list_plans(raion=None), []),
        _safe_call("procurement stats", procurement_statistics(raion=None), {}),
        _safe_call("eu projects", list_projects(status=None, sector=None, raion=None), []),
        _safe_call("eu stats", funding_statistics(), {}),
        _safe_call("statistics", get_statistics_summary(), []),
        _safe_call("catalog", search_sources(q=""), []),
    )

    finance_snapshot = _dump(finance_snapshot)
    weather_snapshot = _dump(weather_snapshot)
    alerts = _dump(alerts)
    tenders = _dump(tenders)
    awards = _dump(awards)
    contracts = _dump(contracts)
    budgets = _dump(budgets)
    plans = _dump(plans)
    procurement_stats = _dump(procurement_stats)
    projects = _dump(projects)
    eu_stats = _dump(eu_stats)
    stats = _dump(stats)
    catalog = _dump(catalog)

    procurement_module = _build_procurement_module(tenders, awards, contracts, budgets, plans, procurement_stats)
    eu_module = _build_eu_module(projects, eu_stats)
    macro_module = _build_macro_module(finance_snapshot, weather_snapshot, alerts, stats)
    discovery_module = _build_discovery_module(catalog)

    modules = [procurement_module, eu_module, macro_module, discovery_module]
    bridge = _bridge_story(tenders, projects)
    live_modules = sum(1 for module in modules if module["state"] == "live")
    total_stories = sum(len(module["stories"]) for module in modules)

    overall_state = "operational" if live_modules >= 2 else "warming up"
    overall_class = "status-live" if overall_state == "operational" else "status-ready"

    hero_metrics = [
        {"label": "modules live", "value": str(live_modules)},
        {"label": "stories", "value": str(total_stories)},
        {"label": "cross-links", "value": str(bridge.get("count", 0))},
        {"label": "catalog items", "value": str(len(catalog))},
    ]

    return {
        "title": "md-data.org / status",
        "subtitle": "Moldova public data API - live atlas for civic data exploration",
        "hero": {
            "eyebrow": "Live atlas",
            "headline": "Explore the data, not the endpoints.",
            "lede": "Civic procurement, EU funding, macro signals, and discovery are surfaced as stories, charts, and cross-links instead of raw JSON dumps.",
        },
        "bridge": bridge,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": {
            "label": overall_state,
            "class_name": overall_class,
        },
        "summary": [
            {"label": "Modules", "value": str(len(modules))},
            {"label": "Stories", "value": str(total_stories)},
            {"label": "Live modules", "value": str(live_modules)},
            {"label": "Cross-links", "value": str(bridge.get("count", 0))},
        ],
        "hero_metrics": hero_metrics,
        "sources": modules,
    }


@router.get("/status", response_class=HTMLResponse, include_in_schema=False)
async def status_page() -> HTMLResponse:
    return HTMLResponse(content=STATUS_HTML)


@router.get("/status/data", include_in_schema=False)
async def status_data() -> dict[str, object]:
    return await build_status_payload()
