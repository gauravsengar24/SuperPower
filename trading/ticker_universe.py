"""Ticker universe — loads ALL US, European, and Indian stocks
with full company names from public CSV sources.

Sources:
  - NASDAQ: nasdaqtrader.com (all listed + microcaps)
  - NYSE: nasdaqtrader.com (all listed + microcaps)
  - OTC: nasdaqtrader.com (OTCQX, OTCQB, Pink)
  - India: NSE via nseindia.com public API
  - Europe: compiled from major exchange listings

Cached locally at ~/.trading/ticker_cache.json (refreshed daily).
"""

import csv
import io
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

CACHE_PATH = Path("~/.trading/ticker_cache.json").expanduser()
CACHE_TTL_HOURS = 24

NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
NYSE_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
OTC_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otclisted.txt"

NSE_EQUITY_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"

EURONEXT_URL = "https://live.euronext.com/sites/default/files/stock-list/Euronext_Equities_All.csv"

LSE_URL = "https://www.londonstockexchange.com/sites/default/files/csv/LSEEquities.csv"


def _download_csv(url: str, skip_rows: int = 0) -> list[dict]:
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        text = resp.text
        for _ in range(skip_rows):
            first_nl = text.find("\n")
            if first_nl == -1:
                return []
            text = text[first_nl + 1:]
        reader = csv.DictReader(io.StringIO(text))
        return [row for row in reader if any(v.strip() for v in row.values())]
    except Exception as e:
        logger.warning("Failed to download %s: %s", url, e)
        return []


def _load_nasdaq() -> list[dict]:
    rows = _download_csv(NASDAQ_URL)
    result = []
    for r in rows:
        symbol = r.get("Symbol", "").strip()
        name = r.get("Security Name", "").strip()
        if symbol and name:
            name = re.sub(r"\s*-\s*Common Stock.*", "", name, flags=re.IGNORECASE)
            name = re.sub(r"\s*-\s*Class [A-Z].*", "", name, flags=re.IGNORECASE)
            result.append({"ticker": symbol, "name": name.strip(), "exchange": "NASDAQ"})
    return result


def _load_nyse() -> list[dict]:
    rows = _download_csv(NYSE_URL)
    result = []
    for r in rows:
        symbol = r.get("ACT Symbol", "").strip()
        name = r.get("Company Name", "").strip()
        exchange = r.get("Exchange", "").strip()
        if symbol and name:
            result.append({"ticker": symbol, "name": name, "exchange": exchange or "NYSE"})
    return result


def _load_otc() -> list[dict]:
    rows = _download_csv(OTC_URL)
    result = []
    for r in rows:
        symbol = r.get("Symbol", "").strip()
        name = r.get("Company Name", "").strip()
        market = r.get("Market Category", "").strip()
        if symbol and name:
            result.append({"ticker": symbol, "name": name, "exchange": f"OTC {market}".strip() or "OTC"})
    return result


def _load_nse() -> list[dict]:
    rows = _download_csv(NSE_EQUITY_URL, skip_rows=1)
    result = []
    for r in rows:
        symbol = r.get("SYMBOL", "").strip()
        name = r.get("NAME OF COMPANY", "").strip()
        if symbol and name:
            result.append({"ticker": f"{symbol}.NS", "name": name, "exchange": "NSE"})
    return result


def _load_euronext() -> list[dict]:
    rows = _download_csv(EURONEXT_URL)
    result = []
    for r in rows:
        symbol = r.get("Symbol", "") or r.get("Code", "")
        name = r.get("Name", "") or r.get("Company name", "")
        market = r.get("Market", "") or "Euronext"
        if symbol and name:
            sym_clean = symbol.strip().replace(" ", "-")
            suffix = ".PA" if "Paris" in market else ".AS" if "Amsterdam" in market else ".BR" if "Brussels" in market else ".LI" if "Lisbon" in market else ".OL" if "Oslo" in market else ".IR" if "Dublin" in market else ""
            result.append({"ticker": f"{sym_clean}{suffix}", "name": name.strip(), "exchange": market.strip()})
    return result


def _load_lse() -> list[dict]:
    rows = _download_csv(LSE_URL)
    result = []
    for r in rows:
        symbol = r.get("TIDM", "") or r.get("Symbol", "")
        name = r.get("Company Name", "") or r.get("Name", "")
        if symbol and name:
            result.append({"ticker": f"{symbol.strip()}.L", "name": name.strip(), "exchange": "LSE"})
    return result


def _load_cache() -> Optional[list[dict]]:
    if CACHE_PATH.exists():
        try:
            data = json.loads(CACHE_PATH.read_text())
            age = time.time() - data.get("ts", 0)
            if age < CACHE_TTL_HOURS * 3600:
                return data.get("tickers", [])
        except (json.JSONDecodeError, KeyError):
            pass
    return None


def _save_cache(tickers: list[dict]):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps({"ts": time.time(), "tickers": tickers}, indent=2))


def get_all_tickers(force_refresh: bool = False) -> list[dict]:
    if not force_refresh:
        cached = _load_cache()
        if cached is not None:
            logger.info("Loaded %d tickers from cache", len(cached))
            return cached

    tickers = []
    for loader, label in [
        (_load_nasdaq, "NASDAQ"),
        (_load_nyse, "NYSE"),
        (_load_otc, "OTC"),
        (_load_nse, "NSE"),
        (_load_euronext, "Euronext"),
        (_load_lse, "LSE"),
    ]:
        try:
            batch = loader()
            logger.info("Loaded %d tickers from %s", len(batch), label)
            tickers.extend(batch)
        except Exception as e:
            logger.warning("Failed to load %s: %s", label, e)

    seen = set()
    unique = []
    for t in tickers:
        key = t["ticker"].upper()
        if key not in seen:
            seen.add(key)
            unique.append(t)

    unique.sort(key=lambda x: x["ticker"])
    logger.info("Total unique tickers: %d", len(unique))

    try:
        _save_cache(unique)
    except Exception as e:
        logger.warning("Failed to save ticker cache: %s", e)

    return unique


def search_tickers(query: str, max_results: int = 50) -> list[dict]:
    all_tickers = get_all_tickers()
    q = query.upper().strip()
    if not q:
        return all_tickers[:max_results]
    results = []
    for t in all_tickers:
        if q in t["ticker"].upper() or q in t["name"].upper():
            results.append(t)
            if len(results) >= max_results:
                break
    if not results:
        results = [t for t in all_tickers[:20]]
    return results


def format_ticker_display(item: dict) -> str:
    return f"{item['ticker']} — {item['name']} ({item.get('exchange', '')})"


def format_ticker_label(item: dict, max_name_len: int = 60) -> str:
    name = item["name"][:max_name_len]
    return f"{item['ticker']:12s} {name}"
