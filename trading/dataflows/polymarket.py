"""Polymarket prediction market data provider.

BUG-8 FIX: Handles both dict and list return types from the Gamma API.
The _request method was annotated as returning dict, but some endpoints
return list. The fix checks the type before calling .get().
"""

from __future__ import annotations

import logging
from typing import Any, Union

logger = logging.getLogger(__name__)

_POLYMARKET_API = "https://gamma-api.polymarket.com"


def _request(endpoint: str, params: Optional[dict] = None) -> Union[dict, list]:
    """Fetch from Polymarket Gamma API.
    
    Returns dict or list depending on the endpoint.
    """
    import requests
    url = f"{_POLYMARKET_API}/{endpoint.lstrip('/')}"
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning("Polymarket error %s: %s", endpoint, e)
        return []


def get_markets(ticker: str, limit: int = 5) -> list[dict]:
    """Get prediction markets related to a ticker."""
    raw = _request("events", {"limit": limit, "tag": ticker})
    if isinstance(raw, dict):
        return raw.get("events", []) if isinstance(raw.get("events"), list) else [raw]
    if isinstance(raw, list):
        events = []
        for item in raw:
            if isinstance(item, dict):
                events.append(item)
        return events
    return []


def get_event_details(event_id: str) -> dict:
    """Get detailed data for a specific event."""
    raw = _request(f"events/{event_id}")
    if isinstance(raw, dict):
        return raw
    return {"error": "Unexpected response format", "raw": raw}
