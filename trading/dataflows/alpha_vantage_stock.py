"""Alpha Vantage stock data provider.

BUG-4 FIX: Uses the requested analysis date to determine outputsize,
not datetime.now(). For backtest dates far in the past, this ensures
"full" output (20+ years) instead of always getting "compact" (100 days).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"


def _should_request_full(analysis_date_str: str) -> bool:
    """Return True if the analysis date is far enough in the past to need full history."""
    try:
        analysis_date = datetime.strptime(analysis_date_str, "%Y-%m-%d")
        age = (datetime.now() - analysis_date).days
        return age > 90
    except (ValueError, TypeError):
        return False


def get_alpha_vantage_data(
    symbol: str,
    analysis_date: str | None = None,
    api_key: str | None = None,
) -> dict:
    """Fetch historical data from Alpha Vantage.
    
    Uses analysis_date (not datetime.now()) to pick outputsize.
    Falls back gracefully if no API key is configured.
    """
    if not api_key:
        logger.warning("No Alpha Vantage API key configured")
        return {"error": "No API key configured"}

    if analysis_date and _should_request_full(analysis_date):
        outputsize = "full"
    else:
        outputsize = "compact"

    import requests
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": symbol,
        "outputsize": outputsize,
        "apikey": api_key,
        "datatype": "json",
    }
    try:
        resp = requests.get(_ALPHA_VANTAGE_BASE, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if "Time Series (Daily)" in data:
            return data
        if "Note" in data:
            logger.warning("Alpha Vantage rate limit: %s", data["Note"])
        return {"error": data.get("Error Message", str(data))}
    except Exception as e:
        logger.warning("Alpha Vantage error for %s: %s", symbol, e)
        return {"error": str(e)}
