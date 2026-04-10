from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from src.api.status import build_status_payload

router = APIRouter()


STATUS_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>md-data.org / status</title>
  <meta name="description" content="Moldova public data API - live explorer for procurement, registries, legislation, geospatial layers, and discovery">
  <style>
    @import url("https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap");

    :root {
      color-scheme: dark;
      --bg: #060d14;
      --bg-2: #0d1722;
      --card: rgba(13, 22, 34, 0.84);
      --card-strong: rgba(11, 18, 28, 0.96);
      --line: rgba(214, 226, 242, 0.12);
      --text: #f4f7fb;
      --muted: #9caac0;
      --muted-strong: #ccd6e4;
      --accent: #76f0bf;
      --accent-2: #f7bf65;
      --accent-3: #85a8ff;
      --accent-4: #f49ac2;
      --shadow: 0 24px 90px rgba(0, 0, 0, 0.42);
      --radius-xl: 30px;
      --radius-lg: 22px;
      --radius-md: 16px;
      --font-display: "Fraunces", "Iowan Old Style", "Palatino Linotype", "Baskerville", serif;
      --font-body: "IBM Plex Sans", "Avenir Next", "Segoe UI", sans-serif;
      --font-mono: "IBM Plex Mono", "SFMono-Regular", "Menlo", monospace;
    }

    * { box-sizing: border-box; }
    html, body { min-height: 100%; }
    body {
      margin: 0;
      color: var(--text);
      background:
        radial-gradient(circle at 12% 10%, rgba(118, 240, 191, 0.13), transparent 22%),
        radial-gradient(circle at 90% 12%, rgba(247, 191, 101, 0.13), transparent 22%),
        radial-gradient(circle at 45% 98%, rgba(133, 168, 255, 0.14), transparent 28%),
        linear-gradient(180deg, #08111b 0%, #05090f 100%);
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
      opacity: 0.18;
      mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.76), rgba(0, 0, 0, 0.06));
    }

    a { color: inherit; }

    .shell {
      position: relative;
      max-width: 1360px;
      margin: 0 auto;
      padding: 18px 18px 36px;
    }

    .topbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 16px;
      margin-bottom: 18px;
    }

    .brand {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      color: var(--muted-strong);
      font-size: 0.76rem;
      font-weight: 700;
      letter-spacing: 0.2em;
      text-transform: uppercase;
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
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }

    .nav-toggle {
      display: none;
    }

    .nav a,
    .button,
    .chip,
    .mini-action,
    .story-action,
    .scenario-card {
      transition: transform 160ms ease, border-color 160ms ease, background 160ms ease, color 160ms ease;
    }

    .nav a {
      text-decoration: none;
      color: var(--muted-strong);
      padding: 9px 12px;
      border-radius: 999px;
      border: 1px solid transparent;
      background: rgba(255, 255, 255, 0.02);
    }

    .nav a:hover,
    .nav a[aria-current="page"] {
      color: var(--text);
      background: rgba(255, 255, 255, 0.04);
      border-color: var(--line);
    }

    .hero {
      display: grid;
      grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.7fr);
      gap: 18px;
      padding: clamp(22px, 3vw, 34px);
      border: 1px solid var(--line);
      border-radius: var(--radius-xl);
      background: linear-gradient(180deg, rgba(13, 22, 34, 0.95), rgba(8, 13, 21, 0.98));
      box-shadow: var(--shadow);
    }

    .eyebrow,
    .section-kicker,
    .bridge-kicker,
    .signal-title {
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 0.68rem;
      font-weight: 700;
    }

    .eyebrow,
    .section-kicker,
    .signal-title,
    .bridge-kicker {
      color: var(--muted);
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 10px;
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
      font-size: clamp(2.6rem, 5.8vw, 5rem);
      line-height: 0.94;
      max-width: 11ch;
    }

    .lede {
      max-width: 70ch;
      margin: 16px 0 0;
      color: var(--muted);
      line-height: 1.62;
      font-size: clamp(0.98rem, 1.18vw, 1.08rem);
    }

    .hero-actions,
    .module-actions,
    .detail-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }

    .hero-actions { margin-top: 22px; }

    .button,
    .chip,
    .mini-action,
    .story-action,
    .scenario-card {
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
      cursor: pointer;
    }

    .button {
      padding: 11px 16px;
      color: var(--text);
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--line);
    }

    .button.primary {
      background: linear-gradient(135deg, rgba(118, 240, 191, 0.14), rgba(118, 240, 191, 0.06));
      border-color: rgba(118, 240, 191, 0.26);
      color: #e7fff5;
    }

    .toggle {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      border-radius: 999px;
      color: var(--muted-strong);
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--line);
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
    .scenario-panel,
    .section-card,
    .detail-card,
    .api-index {
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      background: var(--card);
      backdrop-filter: blur(16px);
      box-shadow: 0 16px 46px rgba(0, 0, 0, 0.24);
    }

    .signal-card,
    .bridge-card,
    .summary-card,
    .scenario-card,
    .module-card,
    .section-card,
    .detail-card,
    .api-index {
      animation: rise 0.55s ease both;
    }

    .signal-card,
    .bridge-card {
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

    .signal-name {
      margin-top: 8px;
      font-family: var(--font-display);
      font-size: 1.5rem;
      line-height: 1.08;
    }

    .signal-body,
    .bridge-detail,
    .section-copy p,
    .scenario-card p,
    .module-detail,
    .story-meta,
    .story-copy,
    .chart-value,
    .summary-label,
    .empty-state {
      color: var(--muted);
      line-height: 1.55;
    }

    .signal-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .signal-stat,
    .summary-card,
    .metric,
    .tag,
    .bridge-pill,
    .scenario-chip,
    .api-link {
      border: 1px solid rgba(255, 255, 255, 0.06);
      background: rgba(255, 255, 255, 0.03);
    }

    .signal-stat {
      padding: 12px;
      border-radius: 16px;
    }

    .signal-stat strong {
      display: block;
      font-size: 1rem;
    }

    .signal-stat span {
      display: block;
      margin-top: 4px;
      font-size: 0.8rem;
      color: var(--muted);
    }

    .bridge-card {
      border-left: 4px solid var(--accent-2);
    }

    .bridge-title {
      font-family: var(--font-display);
      font-size: 1.22rem;
      line-height: 1.12;
    }

    .bridge-row,
    .story-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .bridge-pill,
    .scenario-chip,
    .tag {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 9px;
      border-radius: 999px;
      color: var(--muted-strong);
      font-size: 0.74rem;
    }

    .summary-panel,
    .scenario-panel {
      margin-top: 18px;
      padding: 18px;
    }

    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }

    .summary-card {
      min-height: 110px;
      padding: 16px;
      border-radius: 18px;
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

    .scenario-panel {
      background: linear-gradient(180deg, rgba(18, 29, 44, 0.9), rgba(11, 18, 28, 0.96));
    }

    .scenario-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-top: 14px;
    }

    .scenario-card {
      display: grid;
      gap: 12px;
      padding: 16px;
      border-radius: 22px;
      min-height: 190px;
      color: inherit;
      text-align: left;
      position: relative;
      overflow: hidden;
      background: linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.02));
      border: 1px solid rgba(255, 255, 255, 0.08);
      cursor: pointer;
    }

    .scenario-card::before {
      content: "";
      position: absolute;
      inset: 0 auto auto 0;
      width: 100%;
      height: 3px;
      background: var(--accent, var(--accent-3));
    }

    .scenario-card:hover {
      transform: translateY(-2px);
      border-color: rgba(118, 240, 191, 0.28);
      background: linear-gradient(180deg, rgba(118, 240, 191, 0.06), rgba(255, 255, 255, 0.02));
    }

    .scenario-card.is-active {
      border-color: rgba(118, 240, 191, 0.34);
      box-shadow: 0 18px 56px rgba(0, 0, 0, 0.28);
      background: linear-gradient(180deg, rgba(118, 240, 191, 0.08), rgba(255, 255, 255, 0.02));
    }

    .scenario-card h3 {
      font-size: 1.14rem;
      line-height: 1.15;
      margin-bottom: 8px;
    }

    .scenario-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
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

    .search-wrap span,
    .section-kicker,
    .detail-section h4,
    .api-index summary,
    .signal-title {
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 0.68rem;
      font-weight: 700;
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
      border-radius: 999px;
      cursor: pointer;
    }

    .chip.active {
      color: var(--text);
      background: rgba(118, 240, 191, 0.1);
      border-color: rgba(118, 240, 191, 0.32);
    }

    .content {
      display: grid;
      grid-template-columns: minmax(250px, 0.78fr) minmax(0, 1.28fr) minmax(320px, 0.64fr);
      gap: 16px;
      align-items: start;
    }

    .section-card {
      padding: 18px;
    }

    .navigator-pane {
      position: sticky;
      top: 16px;
      display: grid;
      gap: 12px;
      align-self: start;
    }

    .navigator-overlay {
      display: none;
    }

    .navigator-card {
      padding: 18px;
      border-radius: var(--radius-lg);
      border: 1px solid var(--line);
      background: var(--card);
      backdrop-filter: blur(16px);
      box-shadow: 0 16px 46px rgba(0, 0, 0, 0.24);
      display: grid;
      gap: 14px;
    }

    .navigator-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
    }

    .navigator-head h3 {
      font-size: 1.28rem;
      line-height: 1.1;
      margin-top: 4px;
    }

    .navigator-copy {
      margin: 0;
      color: var(--muted);
      line-height: 1.55;
      font-size: 0.94rem;
    }

    .navigator-stats {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }

    .navigator-stat {
      padding: 12px;
      border-radius: 16px;
      border: 1px solid rgba(255, 255, 255, 0.06);
      background: rgba(255, 255, 255, 0.03);
      display: grid;
      gap: 5px;
    }

    .navigator-stat strong {
      font-size: 1rem;
      letter-spacing: -0.03em;
    }

    .navigator-stat span {
      color: var(--muted);
      font-size: 0.76rem;
      line-height: 1.35;
    }

    .navigator-list {
      display: grid;
      gap: 8px;
    }

    .navigator-item {
      width: 100%;
      text-align: left;
      padding: 12px;
      border-radius: 18px;
      border: 1px solid rgba(255, 255, 255, 0.07);
      background: rgba(255, 255, 255, 0.03);
      color: inherit;
      cursor: pointer;
      display: grid;
      gap: 8px;
    }

    .navigator-item:hover {
      border-color: rgba(118, 240, 191, 0.28);
      background: rgba(118, 240, 191, 0.05);
    }

    .navigator-item.is-active {
      border-color: rgba(118, 240, 191, 0.34);
      background: rgba(118, 240, 191, 0.08);
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2);
    }

    .navigator-item-top {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 10px;
    }

    .navigator-item-title {
      font-weight: 700;
      line-height: 1.18;
    }

    .navigator-item-meta {
      color: var(--muted);
      font-size: 0.8rem;
      line-height: 1.45;
    }

    .navigator-item-foot {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      color: var(--muted-strong);
      font-size: 0.76rem;
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

    .section-copy h2 {
      font-size: clamp(1.55rem, 2vw, 2.4rem);
      line-height: 1.04;
      margin-bottom: 10px;
    }

    .section-state {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 12px;
      border-radius: 999px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 0.78rem;
      font-weight: 700;
      white-space: nowrap;
    }

    .status-live { background: rgba(118, 240, 191, 0.12); color: #adf8dc; }
    .status-ready { background: rgba(133, 168, 255, 0.12); color: #d0dcff; }
    .status-placeholder { background: rgba(247, 191, 101, 0.12); color: #ffe0ad; }
    .status-degraded { background: rgba(255, 140, 154, 0.12); color: #ffbec6; }

    .module-grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
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
      min-height: 0;
      box-shadow: 0 16px 42px rgba(0, 0, 0, 0.22);
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

    .module-card h3 {
      font-size: 1.4rem;
      line-height: 1.1;
      margin-bottom: 8px;
    }

    .module-detail {
      margin: 0;
    }

    .metric-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .metric {
      padding: 12px;
      border-radius: 18px;
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

    .chart-bar {
      display: grid;
      grid-template-columns: minmax(90px, 0.9fr) minmax(0, 1.3fr) auto;
      gap: 10px;
      align-items: center;
      font-size: 0.86rem;
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
    }

    .story-card.is-active {
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
      line-height: 1.2;
      margin-bottom: 6px;
    }

    .story-value {
      color: #e9fff8;
      font-family: var(--font-display);
      font-size: 1.02rem;
      letter-spacing: -0.02em;
      white-space: nowrap;
    }

    .module-actions,
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
      cursor: pointer;
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
      display: grid;
      gap: 10px;
      padding-top: 2px;
    }

    .detail-section h4 {
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 0.68rem;
      font-weight: 700;
    }

    .api-index {
      margin-top: 18px;
      padding: 14px 16px;
    }

    .api-index summary {
      cursor: pointer;
      list-style: none;
      color: var(--muted-strong);
    }

    .api-index summary::-webkit-details-marker { display: none; }

    .source-map-clusters {
      margin-top: 14px;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .source-map-card {
      padding: 14px;
      border-radius: 20px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.03);
      color: inherit;
      cursor: pointer;
      display: grid;
      gap: 10px;
      text-align: left;
    }

    .source-map-card:hover {
      border-color: rgba(118, 240, 191, 0.28);
      background: rgba(118, 240, 191, 0.05);
    }

    .source-map-card.is-active {
      border-color: rgba(118, 240, 191, 0.34);
      background: rgba(118, 240, 191, 0.08);
    }

    .source-map-card-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 12px;
    }

    .source-map-card-title {
      font-size: 1rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.18;
    }

    .source-map-card-copy {
      color: var(--muted);
      font-size: 0.84rem;
      line-height: 1.45;
    }

    .source-map-card-meta {
      display: inline-flex;
      flex-wrap: wrap;
      gap: 6px;
      align-items: center;
      justify-content: flex-end;
    }

    .source-map-active {
      margin-top: 12px;
      display: grid;
      gap: 10px;
      padding-top: 12px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }

    .source-map-active-head {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
    }

    .source-map-active-title {
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      color: var(--muted);
      font-weight: 700;
    }

    .source-map-active-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .source-map-more {
      display: inline-grid;
      gap: 8px;
      align-items: start;
    }

    .source-map-more summary {
      list-style: none;
      cursor: pointer;
      outline: none;
    }

    .source-map-more summary::-webkit-details-marker { display: none; }

    .route-pill.route-pill-more {
      border-style: dashed;
    }

    .source-map-more-panel {
      display: grid;
      gap: 8px;
      padding-left: 10px;
      border-left: 1px solid rgba(255, 255, 255, 0.08);
    }

    .route-more-item {
      display: grid;
      gap: 8px;
      align-items: start;
    }

    .route-more-item summary {
      list-style: none;
      cursor: pointer;
      outline: none;
    }

    .route-more-item summary::-webkit-details-marker { display: none; }

    .route-more-body {
      display: grid;
      gap: 8px;
      padding: 0 6px 2px;
      color: var(--muted);
      font-size: 0.8rem;
      line-height: 1.45;
      max-height: 0;
      opacity: 0;
      overflow: hidden;
      transform: translateY(-2px);
      transition: max-height 180ms ease, opacity 180ms ease, transform 180ms ease;
    }

    .route-more-item:hover .route-more-body,
    .route-more-item:focus-within .route-more-body,
    .route-more-item[open] .route-more-body {
      max-height: 96px;
      opacity: 1;
      transform: translateY(0);
    }

    .route-url {
      font-family: var(--font-mono);
      word-break: break-all;
    }

    .route-open {
      justify-self: start;
      width: 26px;
      height: 26px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: 999px;
      color: var(--muted-strong);
      text-decoration: none;
      border: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.03);
      font-size: 1rem;
      font-weight: 600;
      line-height: 1;
      transition: transform 160ms ease, border-color 160ms ease, background 160ms ease, color 160ms ease;
    }

    .route-open:hover {
      transform: translateY(-1px);
      border-color: rgba(118, 240, 191, 0.28);
      background: rgba(118, 240, 191, 0.06);
      color: var(--text);
    }

    .route-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 12px;
      border-radius: 999px;
      text-decoration: none;
      color: var(--muted-strong);
      border: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.03);
      font-size: 0.84rem;
      line-height: 1.2;
    }

    .route-pill:hover {
      border-color: rgba(118, 240, 191, 0.28);
      background: rgba(118, 240, 191, 0.06);
      color: var(--text);
    }

    .route-pill strong {
      font-size: 0.85rem;
    }

    .route-pill span {
      color: var(--muted);
      font-size: 0.76rem;
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

    .pulse {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--accent);
      box-shadow: 0 0 0 0 rgba(118, 240, 191, 0.45);
      animation: pulse 1.6s infinite;
    }

    .loading-shell {
      display: grid;
      gap: 10px;
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

    .empty-state {
      padding: 20px;
      border-radius: 20px;
      border: 1px dashed rgba(255, 255, 255, 0.14);
      background: rgba(255, 255, 255, 0.02);
    }

    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(118, 240, 191, 0.42); }
      70% { box-shadow: 0 0 0 14px rgba(118, 240, 191, 0); }
      100% { box-shadow: 0 0 0 0 rgba(118, 240, 191, 0); }
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

    @keyframes shimmer {
      0% { background-position: 0 50%; }
      100% { background-position: 200% 50%; }
    }

    @media (max-width: 1100px) {
      .hero,
      .content,
      .explore-bar {
        grid-template-columns: 1fr;
      }

      .navigator-pane {
        position: fixed;
        inset: 0 auto 0 0;
        width: min(392px, 88vw);
        z-index: 40;
        padding: 16px;
        transform: translateX(-105%);
        transition: transform 220ms ease;
        overflow-y: auto;
        background: linear-gradient(180deg, rgba(8, 13, 21, 0.98), rgba(7, 11, 18, 0.99));
        border-right: 1px solid rgba(214, 226, 242, 0.14);
        box-shadow: 24px 0 60px rgba(0, 0, 0, 0.4);
      }

      body.nav-open .navigator-pane {
        transform: translateX(0);
      }

      .navigator-overlay {
        display: block;
        position: fixed;
        inset: 0;
        z-index: 30;
        background: rgba(2, 5, 10, 0.62);
        backdrop-filter: blur(4px);
        opacity: 0;
        pointer-events: none;
        transition: opacity 180ms ease;
      }

      body.nav-open .navigator-overlay {
        opacity: 1;
        pointer-events: auto;
      }

      .nav-toggle {
        display: inline-flex;
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

      .nav-toggle {
        align-self: stretch;
        width: 100%;
      }

      .summary-grid,
      .scenario-grid,
      .module-grid,
      .metric-grid,
      .signal-grid,
      .api-grid {
        grid-template-columns: 1fr;
      }

      .hero-actions,
      .module-actions,
      .detail-actions {
        flex-direction: column;
        align-items: stretch;
      }

      .chart-bar {
        grid-template-columns: 1fr;
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
  <div class="navigator-overlay" data-action="toggle-nav" aria-hidden="true"></div>
  <div class="shell">
    <header class="topbar" aria-label="Primary">
      <div class="brand">
        <span class="brand-mark" aria-hidden="true"></span>
        md-data.org
      </div>
      <nav class="nav">
        <a href="/">Home</a>
        <a href="/docs">API Docs</a>
        <a href="#scenarios">Scenarios</a>
        <a href="#families">Families</a>
        <a href="#modules">Modules</a>
        <a href="/v1/search">Discovery</a>
        <a href="/status" aria-current="page">Status</a>
      </nav>
      <button class="button nav-toggle" type="button" data-action="toggle-nav">Sources</button>
    </header>

    <section class="hero" aria-label="Status overview">
      <div class="hero-copy">
        <div class="eyebrow">
          <span class="eyebrow-dot" aria-hidden="true"></span>
          live atlas · civic data exploration
        </div>
        <h1>Explore the data, not the endpoints.</h1>
        <p class="lede" id="hero-lede">
          Civic procurement, open data, registries, legislation, geospatial layers, EU funding, and macro signals are
          surfaced as stories and pathways instead of raw JSON dumps.
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
          <div class="bridge-detail" id="bridge-detail">Procurement and EU funding links will appear once the payload loads.</div>
          <div class="bridge-row" id="bridge-actions"></div>
        </section>
      </div>
    </section>

    <section class="scenario-panel" id="scenarios" aria-labelledby="scenarios-title">
      <div class="section-head">
        <div class="section-copy">
          <div class="section-kicker">Scenario deck</div>
          <h2 id="scenarios-title">Choose an entry point into the atlas</h2>
          <p>Each card maps a user intent to the best source family, so the page reads like a guide rather than a dump.</p>
        </div>
        <div class="section-state status-ready" id="scenario-count">0 pathways</div>
      </div>
      <div class="scenario-grid" id="scenario-grid"></div>
    </section>

    <section class="summary-panel" id="families" aria-label="Summary">
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
      <aside class="navigator-pane" aria-label="Source family navigator">
        <section class="navigator-card">
          <div class="navigator-head">
            <div>
              <div class="section-kicker">Source map</div>
              <h3>Navigate by family</h3>
            </div>
            <button class="mini-action primary" type="button" data-action="reset-view">Reset</button>
          </div>
          <p class="navigator-copy" id="navigator-copy">Use the family rail to jump directly into a source family or clear the lens to explore everything.</p>
          <div class="navigator-stats" id="navigator-stats"></div>
        </section>

        <section class="navigator-card">
          <div class="navigator-head">
            <div>
              <div class="section-kicker">Families</div>
              <h3>Pick a source family</h3>
            </div>
            <div class="section-state status-ready" id="navigator-count">0 families</div>
          </div>
          <div class="navigator-list" id="navigator-list"></div>
        </section>

        <section class="navigator-card">
          <div class="navigator-head">
            <div>
              <div class="section-kicker">Current path</div>
              <h3 id="navigator-path-title">Loading...</h3>
            </div>
            <div class="section-state status-placeholder" id="navigator-path-state">path</div>
          </div>
          <p class="navigator-copy" id="navigator-path-copy">The current scenario will appear here after the payload loads.</p>
          <div class="detail-actions" id="navigator-path-actions"></div>
        </section>
      </aside>

      <section class="section-card" id="modules" aria-labelledby="board-title">
        <div class="section-head">
          <div class="section-copy">
            <div class="section-kicker">Family explorer</div>
            <h2 id="board-title">Live families, surfaced as stories</h2>
            <p>
              Each card turns a source family into a guided entry point: metrics, linked records, and a small set of
              narrative routes instead of a stack of raw endpoints.
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
      <summary>Source map</summary>
      <p class="navigator-copy" style="margin: 12px 0 0;">Grouped route clusters for each source family. Open only the cluster you need.</p>
      <div class="source-map-clusters" id="api-grid"></div>
      <div class="source-map-active" id="api-deep-links"></div>
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
      activeScenarioId: null,
      activeModuleId: null,
      activeStoryId: null,
      navOpen: false,
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
      procurement: "Procurement",
      eu: "EU funds",
      registers: "Registers",
      legislation: "Legislation",
      geospatial: "Geospatial",
      datasets: "Open data",
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

    const formatDate = (value) => {
      if (!value) return "Unknown";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return String(value);
      return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
    };

    const formatAmount = (amount, currency) => {
      if (amount === null || amount === undefined) return "—";
      const number = Number(amount);
      const abs = Math.abs(number);
      let scaled = number;
      let suffix = "";
      if (abs >= 1_000_000_000) { scaled = number / 1_000_000_000; suffix = "B"; }
      else if (abs >= 1_000_000) { scaled = number / 1_000_000; suffix = "M"; }
      else if (abs >= 1_000) { scaled = number / 1_000; suffix = "K"; }
      return suffix ? `${scaled.toFixed(1)}${suffix} ${currency || ""}`.trim() : `${number.toLocaleString()} ${currency || ""}`.trim();
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
        if (!query) return true;
        const haystack = [
          module.name,
          module.kind,
          module.detail,
          module.note,
          ...(module.highlights || []),
          ...(module.metrics || []).map((metric) => `${metric.label} ${metric.value} ${metric.hint || ""}`),
          ...(module.stories || []).flatMap((story) => [story.title, story.meta, story.value, story.blurb, story.detail, story.route, story.route_label, ...(story.tags || [])]),
          ...(module.routes || []).flatMap((route) => [route.label, route.href])
        ].join(" ").toLowerCase();
        return haystack.includes(query);
      });
    };

    const setStatusBadge = (element, stateName) => {
      const raw = String(stateName || "placeholder");
      const className = raw.startsWith("status-") ? raw : (stateStyles[raw] || stateStyles.placeholder);
      element.className = `section-state ${className}`;
      element.textContent = raw.replace(/^status-/, "");
    };

    const setNavigatorOpen = (open) => {
      state.navOpen = Boolean(open);
      document.body.classList.toggle("nav-open", state.navOpen);
    };

    const renderSummary = () => {
      const grid = document.getElementById("summary-grid");
      const items = state.data?.summary || [];
      grid.innerHTML = items.map((item) => `
        <article class="summary-card">
          <div class="summary-value">${escapeHtml(item.value)}</div>
          <div class="summary-label">${escapeHtml(item.label)}</div>
        </article>
      `).join("");
    };

    const renderHero = () => {
      const metrics = state.data?.hero_metrics || [];
      document.getElementById("hero-metrics").innerHTML = metrics.map((item) => `
        <div class="signal-stat">
          <strong>${escapeHtml(item.value)}</strong>
          <span>${escapeHtml(item.label)}</span>
        </div>
      `).join("");

      const bridge = state.data?.bridge || {};
      document.getElementById("bridge-title").textContent = bridge.title || "Cross-link spotlight";
      document.getElementById("bridge-detail").textContent = bridge.detail || "No bridge data available.";
      const actions = [];
      if (bridge.project?.route) actions.push(`<a class="bridge-pill" href="${escapeHtml(bridge.project.route)}">${escapeHtml(bridge.project.title || "Open project")}</a>`);
      if (bridge.tender?.route) actions.push(`<a class="bridge-pill" href="${escapeHtml(bridge.tender.route)}">${escapeHtml(bridge.tender.title || "Open tender")}</a>`);
      if (!actions.length) actions.push(`<span class="bridge-pill">Bridge will appear when links are present</span>`);
      document.getElementById("bridge-actions").innerHTML = actions.join("");
    };

    const renderScenarios = () => {
      const grid = document.getElementById("scenario-grid");
      const scenarios = state.data?.scenarios || [];
      document.getElementById("scenario-count").textContent = `${scenarios.length} pathway${scenarios.length === 1 ? "" : "s"}`;

      grid.innerHTML = scenarios.map((scenario, index) => `
        <article class="scenario-card${scenario.id === state.activeScenarioId ? " is-active" : ""}" style="--accent:${escapeHtml(scenario.accent || "#85a8ff")}; animation-delay:${index * 60}ms;">
          <div>
            <div class="section-kicker">${escapeHtml(scenario.kicker || "Scenario")}</div>
            <h3>${escapeHtml(scenario.title)}</h3>
            <p>${escapeHtml(scenario.description || "")}</p>
          </div>
          <div class="scenario-meta">
            <span class="scenario-chip">${escapeHtml(filterLabels[scenario.filter] || scenario.filter || "All")}</span>
            <span class="scenario-chip">${escapeHtml(scenario.module_id || "module")}</span>
            <span class="scenario-chip">${escapeHtml(scenario.query || "search")}</span>
          </div>
          <div class="detail-actions">
            <button class="story-action primary" type="button" data-action="select-scenario" data-scenario-id="${escapeHtml(scenario.id)}">Explore this path</button>
            ${(scenario.routes || []).slice(0, 2).map((route) => `<a class="story-action" href="${escapeHtml(route.href)}">${escapeHtml(route.label)}</a>`).join("")}
          </div>
        </article>
      `).join("");
    };

    const renderNavigator = () => {
      const sources = state.data?.sources || [];
      const visible = getVisibleModules();
      const crossLinkedFamilies = sources.filter((module) => Number(module.cross_link_count || 0) > 0).length;
      const totalCrossLinks = sources.reduce((sum, module) => sum + Number(module.cross_link_count || 0), 0);

      document.getElementById("navigator-copy").textContent = state.query
        ? `Filtered to ${filterLabels[state.filter] || state.filter || "All"} with “${state.query}”.`
        : `Showing ${filterLabels[state.filter] || state.filter || "All"} across ${sources.length} source families.`;

      document.getElementById("navigator-stats").innerHTML = [
        {
          value: `${visible.length}/${sources.length}`,
          label: "Visible families",
          hint: "match the current lens",
        },
        {
          value: state.data?.summary?.[1]?.value || "0",
          label: "Scenarios",
          hint: "guided entry points",
        },
        {
          value: String(crossLinkedFamilies),
          label: "Linked families",
          hint: "source pairs with bridges",
        },
        {
          value: String(totalCrossLinks),
          label: "Cross-links",
          hint: "all linked stories",
        },
      ].map((item) => `
        <div class="navigator-stat">
          <strong>${escapeHtml(item.value)}</strong>
          <span>${escapeHtml(item.label)} · ${escapeHtml(item.hint)}</span>
        </div>
      `).join("");

      document.getElementById("navigator-count").textContent = `${sources.length} family${sources.length === 1 ? "" : "ies"}`;

      const sorted = [...sources].sort((left, right) => {
        const leftActive = left.id === state.activeModuleId || left.kind === state.filter ? 1 : 0;
        const rightActive = right.id === state.activeModuleId || right.kind === state.filter ? 1 : 0;
        return (
          rightActive - leftActive ||
          Number(right.cross_link_count || 0) - Number(left.cross_link_count || 0) ||
          (left.name || "").localeCompare(right.name || "")
        );
      });

      document.getElementById("navigator-list").innerHTML = sorted.map((module) => {
        const isActive = module.id === state.activeModuleId || module.kind === state.filter;
        const primaryMetric = (module.metrics || [])[0];
        const routes = module.routes || [];
        const metricText = primaryMetric ? `${primaryMetric.value} ${primaryMetric.label}` : `${routes.length} route(s)`;
        return `
          <button class="navigator-item${isActive ? " is-active" : ""}" type="button" data-action="select-family" data-module-id="${escapeHtml(module.id)}">
            <div class="navigator-item-top">
              <div>
                <div class="navigator-item-title">${escapeHtml(module.name)}</div>
                <div class="navigator-item-meta">${escapeHtml(module.detail || module.note || "")}</div>
              </div>
              <span class="section-state ${stateStyles[module.state] || stateStyles.placeholder}">${escapeHtml(module.state || "ready")}</span>
            </div>
            <div class="navigator-item-foot">
              <span>${escapeHtml(metricText)}</span>
              <span>${escapeHtml(String(module.cross_link_count || 0))} link(s)</span>
            </div>
          </button>
        `;
      }).join("");

      const scenarios = state.data?.scenarios || [];
      const currentScenario =
        scenarios.find((item) => item.id === state.activeScenarioId) ||
        scenarios.find((item) => item.module_id === state.activeModuleId) ||
        scenarios.find((item) => item.filter === state.filter) ||
        scenarios[0] ||
        null;

      const pathTitle = document.getElementById("navigator-path-title");
      const pathCopy = document.getElementById("navigator-path-copy");
      const pathState = document.getElementById("navigator-path-state");
      const pathActions = document.getElementById("navigator-path-actions");

      if (!currentScenario) {
        pathTitle.textContent = "No path selected";
        pathCopy.textContent = "Choose a scenario or source family to shape the board.";
        setStatusBadge(pathState, "placeholder");
        pathActions.innerHTML = `<span class="bridge-pill">Use the deck or source map to choose a path</span>`;
        return;
      }

      pathTitle.textContent = currentScenario.title;
      pathCopy.textContent = currentScenario.description || "Guided scenario path.";
      setStatusBadge(pathState, "live");
      const actions = [];
      if (currentScenario.routes) {
        actions.push(
          ...currentScenario.routes.slice(0, 2).map(
            (route) => `<a class="story-action" href="${escapeHtml(route.href)}">${escapeHtml(route.label)}</a>`,
          ),
        );
      }
      if (currentScenario.module_id) {
        actions.push(
          `<button class="story-action primary" type="button" data-action="select-family" data-module-id="${escapeHtml(currentScenario.module_id)}">Open family</button>`,
        );
      }
      pathActions.innerHTML = actions.join("");
    };

    const renderModuleTabs = () => {
      const row = document.getElementById("filter-row");
      row.innerHTML = Object.entries(filterLabels).map(([key, label]) => `
        <button
          class="chip${state.filter === key ? " active" : ""}"
          type="button"
          data-action="set-filter"
          data-filter="${escapeHtml(key)}"
          aria-pressed="${state.filter === key ? "true" : "false"}"
        >${escapeHtml(label)}</button>
      `).join("");
    };

    const renderApiIndex = () => {
      const grid = document.getElementById("api-grid");
      const deep = document.getElementById("api-deep-links");
      const modules = state.data?.sources || [];
      const activeModule = modules.find((module) => module.id === state.activeModuleId) || modules[0] || null;

      grid.innerHTML = modules.map((module) => {
        const routes = module.routes || [];
        return `
          <button class="source-map-card${module.id === (activeModule?.id || "") ? " is-active" : ""}" type="button" data-action="select-source-map" data-module-id="${escapeHtml(module.id)}">
            <div class="source-map-card-top">
              <div>
                <div class="source-map-card-title">${escapeHtml(module.name)}</div>
                <div class="source-map-card-copy">${escapeHtml(module.detail || module.note || "Route family cluster")}</div>
              </div>
              <div class="source-map-card-meta">
                <span class="section-state ${stateStyles[module.state] || stateStyles.placeholder}">${escapeHtml(module.state || "ready")}</span>
                <span class="bridge-pill">${escapeHtml(String(routes.length))} route${routes.length === 1 ? "" : "s"}</span>
              </div>
            </div>
            <div class="route-cluster-note" style="color: var(--muted); font-size: 0.8rem; line-height: 1.45;">
              ${escapeHtml(module.kicker || module.kind || "source family")} · ${escapeHtml(String(module.cross_link_count || 0))} link(s)
            </div>
          </button>
        `;
      }).join("");

      if (!activeModule) {
        deep.innerHTML = `<div class="empty-state">Select a family card to reveal its deep links.</div>`;
        return;
      }

      const activeRoutes = activeModule.routes || [];
      const primaryRoutes = activeRoutes.slice(0, 2);
      const extraRoutes = activeRoutes.slice(2);
      deep.innerHTML = `
        <div class="source-map-active-head">
          <div>
            <div class="source-map-active-title">Deep links · ${escapeHtml(activeModule.name)}</div>
            <div class="navigator-copy" style="margin: 6px 0 0;">Only the active family routes are shown here.</div>
          </div>
          <span class="bridge-pill">${escapeHtml(String(activeRoutes.length))} route${activeRoutes.length === 1 ? "" : "s"}</span>
        </div>
        <div class="source-map-active-row">
          ${primaryRoutes.map((route) => `
            <a class="route-pill" href="${escapeHtml(route.href)}">
              <strong>${escapeHtml(route.label)}</strong>
              <span>${escapeHtml(route.href)}</span>
            </a>
          `).join("")}
          ${extraRoutes.length ? `
            <details class="source-map-more">
              <summary class="route-pill route-pill-more">More <span>+${escapeHtml(String(extraRoutes.length))}</span></summary>
              <div class="source-map-more-panel">
                ${extraRoutes.map((route) => `
                  <details class="route-more-item">
                    <summary class="route-pill">${escapeHtml(route.label)}</summary>
                    <div class="route-more-body">
                      <div class="route-url">${escapeHtml(route.href)}</div>
                      <a class="route-open" href="${escapeHtml(route.href)}" aria-label="Open route ${escapeHtml(route.label)}" title="Open route ${escapeHtml(route.label)}">›</a>
                    </div>
                  </details>
                `).join("")}
              </div>
            </details>
          ` : ""}
        </div>
      `;
    };

    const renderDetail = (module) => {
      const detail = document.getElementById("detail-panel");
      if (!module) {
        detail.innerHTML = `<div class="empty-state">No module selected. Use the search box or the filter chips to focus the explorer.</div>`;
        return;
      }

      const selectedStory = (module.stories || []).find((story) => story.id === state.activeStoryId) || module.stories?.[0] || null;
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
          ${(module.routes || []).map((route) => `<a class="mini-action" href="${escapeHtml(route.href)}">${escapeHtml(route.label)}</a>`).join("")}
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
          ` : `<div class="empty-state">This module does not have a selected story yet.</div>`}
        </div>

        <div class="detail-section">
          <h4>Visual balance</h4>
          <div class="chart">
            ${moduleChart.map((item) => `
              <div class="chart-bar">
                <div class="chart-label">${escapeHtml(item.label)}</div>
                <div class="chart-track"><div class="chart-fill" style="width:${escapeHtml(item.width)}%;"></div></div>
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
      count.textContent = `${visible.length} family${visible.length === 1 ? "" : "ies"} visible`;

      if (!visible.length) {
        grid.innerHTML = `<div class="empty-state" style="grid-column: 1 / -1;">No modules matched your search. Try a different query or reset the filter chips.</div>`;
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
                <div class="section-kicker">${escapeHtml(module.kicker || module.kind || "")}</div>
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
                  <div class="chart-track"><div class="chart-fill" style="width:${escapeHtml(item.width)}%;"></div></div>
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
              ${(module.routes || []).slice(0, 3).map((route) => `<a class="mini-action" href="${escapeHtml(route.href)}">${escapeHtml(route.label)}</a>`).join("")}
            </div>
          </article>
        `;
      }).join("");

      renderDetail(selectedModule);
    };

    const renderAll = () => {
      if (!state.data) return;
      const overall = state.data.overall || {};
      const overallStatus = document.getElementById("overall-status");
      const overallState = document.getElementById("overall-state");
      overallStatus.innerHTML = `<span class="pulse" aria-hidden="true"></span> ${escapeHtml(overall.label || "operational")}`;
      setStatusBadge(overallState, overall.class_name || "live");
      document.getElementById("generated-meta").textContent =
        `Updated ${formatDate(state.data.generated_at)} · ${state.data.summary?.[0]?.value || 0} families · ${state.data.summary?.[1]?.value || 0} scenarios · ${state.data.summary?.[2]?.value || 0} live families`;
      document.getElementById("hero-lede").textContent = state.data.hero?.lede || document.getElementById("hero-lede").textContent;
      renderHero();
      renderScenarios();
      renderSummary();
      renderModuleTabs();
      renderNavigator();
      renderModules();
      renderApiIndex();
      document.getElementById("module-count").textContent = `${getVisibleModules().length} family${getVisibleModules().length === 1 ? "" : "ies"} visible`;
    };

    const hydrate = async () => {
      try {
        document.getElementById("refresh-button").textContent = "Refreshing...";
        const response = await fetch("/status/data", { headers: { accept: "application/json" } });
        if (!response.ok) throw new Error(`Status payload returned ${response.status}`);
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
        document.getElementById("module-grid").innerHTML = `<div class="empty-state" style="grid-column: 1 / -1;">The explorer could not load its payload. Refresh after confirming the API is running.</div>`;
        document.getElementById("detail-panel").innerHTML = `<div class="empty-state">No detail view is available because the payload failed to load.</div>`;
      } finally {
        document.getElementById("refresh-button").textContent = "Refresh now";
      }
    };

    const bindEvents = () => {
      document.getElementById("refresh-button").addEventListener("click", () => hydrate());

      document.querySelectorAll("[data-action='toggle-nav']").forEach((button) => {
        button.addEventListener("click", () => setNavigatorOpen(!state.navOpen));
      });

      document.querySelector(".navigator-overlay")?.addEventListener("click", () => setNavigatorOpen(false));

      document.getElementById("auto-refresh").addEventListener("change", (event) => {
        state.autoRefresh = event.target.checked;
        if (state.refreshTimer) {
          clearInterval(state.refreshTimer);
          state.refreshTimer = null;
        }
        if (state.autoRefresh) {
          state.refreshTimer = setInterval(() => hydrate(), 120000);
        }
      });

      document.getElementById("search-input").addEventListener("input", (event) => {
        state.query = event.target.value;
        state.activeScenarioId = null;
        renderScenarios();
        renderNavigator();
        renderModules();
      });

      document.getElementById("filter-row").addEventListener("click", (event) => {
        const button = event.target.closest("[data-action='set-filter']");
        if (!button) return;
        state.filter = button.dataset.filter || "all";
        state.activeScenarioId = null;
        renderModuleTabs();
        renderScenarios();
        renderNavigator();
        renderModules();
      });

      document.getElementById("scenario-grid").addEventListener("click", (event) => {
        const scenarioButton = event.target.closest("[data-action='select-scenario']");
        if (!scenarioButton) return;
        const scenario = (state.data?.scenarios || []).find((item) => item.id === scenarioButton.dataset.scenarioId);
        if (!scenario) return;

        state.activeScenarioId = scenario.id;
        state.filter = scenario.filter || "all";
        state.query = scenario.query || "";
        state.activeModuleId = scenario.module_id || null;
        state.activeStoryId = null;

        const searchInput = document.getElementById("search-input");
        if (searchInput) {
          searchInput.value = state.query;
        }

        renderModuleTabs();
        renderScenarios();
        renderNavigator();
        renderModules();
        setNavigatorOpen(false);
        document.getElementById("modules").scrollIntoView({ behavior: "smooth", block: "start" });
      });

      document.getElementById("navigator-list").addEventListener("click", (event) => {
        const familyButton = event.target.closest("[data-action='select-family']");
        if (!familyButton) return;
        const moduleId = familyButton.dataset.moduleId;
        const module = (state.data?.sources || []).find((item) => item.id === moduleId);
        if (!module) return;

        state.filter = module.kind || module.id || "all";
        state.query = "";
        state.activeModuleId = module.id;
        state.activeStoryId = module.stories?.[0]?.id || null;
        const matchingScenario = (state.data?.scenarios || []).find((item) => item.module_id === module.id || item.filter === module.kind);
        state.activeScenarioId = matchingScenario?.id || null;

        const searchInput = document.getElementById("search-input");
        if (searchInput) {
          searchInput.value = "";
        }

        renderModuleTabs();
        renderScenarios();
        renderNavigator();
        renderModules();
        setNavigatorOpen(false);
        document.getElementById("modules").scrollIntoView({ behavior: "smooth", block: "start" });
      });

      document.getElementById("api-grid").addEventListener("click", (event) => {
        const familyButton = event.target.closest("[data-action='select-source-map']");
        if (!familyButton) return;
        const moduleId = familyButton.dataset.moduleId;
        const module = (state.data?.sources || []).find((item) => item.id === moduleId);
        if (!module) return;

        state.filter = module.kind || module.id || "all";
        state.query = "";
        state.activeModuleId = module.id;
        state.activeStoryId = module.stories?.[0]?.id || null;
        const matchingScenario = (state.data?.scenarios || []).find((item) => item.module_id === module.id || item.filter === module.kind);
        state.activeScenarioId = matchingScenario?.id || null;

        const searchInput = document.getElementById("search-input");
        if (searchInput) {
          searchInput.value = "";
        }

        renderModuleTabs();
        renderScenarios();
        renderNavigator();
        renderModules();
        renderApiIndex();
        setNavigatorOpen(false);
        document.getElementById("modules").scrollIntoView({ behavior: "smooth", block: "start" });
      });

      const navigatorPane = document.querySelector(".navigator-pane");
      navigatorPane?.addEventListener("click", (event) => {
        const resetButton = event.target.closest("[data-action='reset-view']");
        if (!resetButton) return;

        state.query = "";
        state.filter = "all";
        state.activeScenarioId = null;
        state.activeModuleId = null;
        state.activeStoryId = null;

        const searchInput = document.getElementById("search-input");
        if (searchInput) {
          searchInput.value = "";
        }

        renderModuleTabs();
        renderScenarios();
        renderNavigator();
        renderModules();
        setNavigatorOpen(false);
      });

      document.getElementById("module-grid").addEventListener("click", (event) => {
        const moduleButton = event.target.closest("[data-action='select-module']");
        if (moduleButton) {
          state.activeModuleId = moduleButton.dataset.moduleId;
          const module = (state.data?.sources || []).find((item) => item.id === state.activeModuleId);
          state.activeStoryId = module?.stories?.[0]?.id || null;
          state.activeScenarioId = (state.data?.scenarios || []).find((item) => item.module_id === state.activeModuleId || item.filter === module?.kind)?.id || state.activeScenarioId;
          renderNavigator();
          renderModules();
          return;
        }

        const storyButton = event.target.closest("[data-action='select-story']");
        if (storyButton) {
          state.activeModuleId = storyButton.dataset.moduleId;
          state.activeStoryId = storyButton.dataset.storyId;
          const module = (state.data?.sources || []).find((item) => item.id === state.activeModuleId);
          state.activeScenarioId = (state.data?.scenarios || []).find((item) => item.module_id === state.activeModuleId || item.filter === module?.kind)?.id || state.activeScenarioId;
          renderNavigator();
          renderModules();
        }
      });

      document.getElementById("detail-panel").addEventListener("click", async (event) => {
        const copyButton = event.target.closest("[data-action='copy-route']");
        if (!copyButton) return;
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
      state.refreshTimer = setInterval(() => hydrate(), 120000);
    }
  </script>
</body>
</html>
"""


@router.get("/status", response_class=HTMLResponse, include_in_schema=False)
async def status_page() -> HTMLResponse:
    return HTMLResponse(content=STATUS_HTML)


@router.get("/status/data", include_in_schema=False)
async def status_data() -> dict[str, object]:
    return await build_status_payload()
