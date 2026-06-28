from __future__ import annotations

"""World Bank API — macroeconomic indicators by country.

Fetches GDP, inflation, unemployment, debt, and other country-level
economic data for agent research.
"""

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_API_BASE = "https://api.worldbank.org/v2"
_TIMEOUT = 15

# (indicator_id, label)
DEFAULT_INDICATORS: list[tuple[str, str]] = [
    ("NY.GDP.MKTP.CD", "GDP (current US$)"),
    ("NY.GDP.MKTP.KD.ZG", "GDP growth (annual %)"),
    ("NY.GDP.PCAP.CD", "GDP per capita (current US$)"),
    ("FP.CPI.TOTL.ZG", "Inflation, consumer prices (annual %)"),
    ("SL.UEM.TOTL.ZS", "Unemployment (% of total labor force)"),
    ("GC.DOD.TOTL.GD.ZS", "Central government debt (% of GDP)"),
    ("BN.CAB.XOKA.GD.ZS", "Current account balance (% of GDP)"),
    ("BX.KLT.DINV.WD.GD.ZS", "Foreign direct investment (% of GDP)"),
    ("NE.EXP.GNFS.KD.ZG", "Exports of goods and services (annual %)"),
    ("SP.POP.TOTL", "Population, total"),
]

_INDICATOR_REGISTRY = {code: label for code, label in DEFAULT_INDICATORS}

# Common ticker → country name mappings for World Bank lookup
# Fallback when yfinance is unavailable
_COUNTRY_HINTS: dict[str, str] = {}


def _country_from_ticker(ticker: str) -> Optional[str]:
    """Resolve a ticker symbol to a country name via yfinance info."""
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        country = info.get("country") or _COUNTRY_HINTS.get(ticker.upper())
        return country
    except Exception:
        return _COUNTRY_HINTS.get(ticker.upper())


def _country_to_iso2(country_name: str) -> Optional[str]:
    """Map a country name to its ISO 3166-1 alpha-2 code."""
    mapping = {
        "united states": "US",
        "usa": "US",
        "india": "IN",
        "china": "CN",
        "japan": "JP",
        "germany": "DE",
        "united kingdom": "GB",
        "uk": "GB",
        "france": "FR",
        "canada": "CA",
        "australia": "AU",
        "brazil": "BR",
        "south korea": "KR",
        "russia": "RU",
        "switzerland": "CH",
        "netherlands": "NL",
        "sweden": "SE",
        "norway": "NO",
        "denmark": "DK",
        "singapore": "SG",
        "hong kong": "HK",
        "taiwan": "TW",
        "south africa": "ZA",
        "mexico": "MX",
        "indonesia": "ID",
        "turkey": "TR",
        "saudi arabia": "SA",
        "uae": "AE",
        "argentina": "AR",
        "italy": "IT",
        "spain": "ES",
        "portugal": "PT",
        "belgium": "BE",
        "austria": "AT",
        "finland": "FI",
        "ireland": "IE",
        "new zealand": "NZ",
        "israel": "IL",
        "malaysia": "MY",
        "thailand": "TH",
        "vietnam": "VN",
        "philippines": "PH",
        "pakistan": "PK",
        "bangladesh": "BD",
        "nigeria": "NG",
        "egypt": "EG",
        "chile": "CL",
        "colombia": "CO",
        "peru": "PE",
        "poland": "PL",
        "czech republic": "CZ",
        "hungary": "HU",
        "romania": "RO",
        "greece": "GR",
        "kenya": "KE",
        "morocco": "MA",
    }
    return mapping.get(country_name.strip().lower())


def _fetch_indicator(country_code: str, indicator: str, years: int) -> Optional[list]:
    """Fetch a single indicator from the World Bank API."""
    try:
        end_year = 2026
        start_year = end_year - years
        url = (
            f"{_API_BASE}/country/{country_code}/indicator/{indicator}"
            f"?format=json&per_page=100&date={start_year}:{end_year}"
        )
        resp = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data or not isinstance(data, list) or len(data) < 2:
            return None
        return data[1]
    except Exception as e:
        logger.warning("World Bank fetch error: %s", e)
        return None


def get_macro_economic_data(ticker_or_country: str, years: int = 5,
                            indicators: str = "all") -> str:
    """Fetch macroeconomic indicators from the World Bank.

    Use this to get country-level economic context: GDP, inflation,
    unemployment, debt, trade balance, population, etc.

    Args:
        ticker_or_country: A stock ticker (e.g. AAPL) or country name.
        years: Number of years of historical data (default 5).
        indicators: Comma-separated indicator names or "all" for defaults.
            Available: GDP, GDP growth, GDP per capita, Inflation,
            Unemployment, Government debt, Current account, FDI, Exports, Population.

    Returns:
        Formatted text table of indicator values, or an error message.
    """
    country = _country_from_ticker(ticker_or_country)
    if not country:
        country = ticker_or_country
    iso2 = _country_to_iso2(country)
    if not iso2:
        return f"Could not map '{ticker_or_country}' to a World Bank country. Try a country name like 'United States', 'India', 'Japan'."

    if indicators.strip().lower() in ("all", ""):
        selected = DEFAULT_INDICATORS
    else:
        selected = []
        for name in indicators.split(","):
            name = name.strip().lower()
            for code, label in DEFAULT_INDICATORS:
                if name in label.lower():
                    selected.append((code, label))
                    break

    if not selected:
        return f"No known indicators matched '{indicators}'. Available: {', '.join(label for _, label in DEFAULT_INDICATORS)}"

    lines: list[str] = [f"World Bank — {country.title()} ({iso2})"]
    lines.append(f"Period: last {years} years\n")

    for code, label in selected:
        raw = _fetch_indicator(iso2, code, years)
        if not raw:
            lines.append(f"  {label}: No data")
            continue
        values = []
        for entry in raw:
            year = entry.get("date", "")
            value = entry.get("value")
            if value is not None:
                try:
                    if code == "SP.POP.TOTL":
                        values.append(f"{year}: {float(value):,.0f}")
                    elif "ZG" in code or "ZS" in code:
                        values.append(f"{year}: {float(value):.2f}%")
                    else:
                        values.append(f"{year}: ${float(value):,.2f}")
                except (ValueError, TypeError):
                    values.append(f"{year}: {value}")
        if values:
            lines.append(f"  {label}:  {' | '.join(values[::-1])}")
        else:
            lines.append(f"  {label}: No data")

    return "\n".join(lines)


def list_available_indicators() -> str:
    """List all available World Bank indicators that can be queried."""
    lines = ["World Bank Indicators:", ""]
    for code, label in DEFAULT_INDICATORS:
        lines.append(f"  {code} — {label}")
    return "\n".join(lines)
