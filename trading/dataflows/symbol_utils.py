"""Symbol normalization utilities."""

import re

# Broker symbol → Yahoo Finance symbol mappings
_SYMBOL_MAP = {
    "XAUUSD": "GC=F",
    "XAGUSD": "SI=F",
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SPX": "^GSPC",
    "NDX": "^IXIC",
    "DJI": "^DJI",
    "VIX": "^VIX",
    "US10Y": "^TNX",
    "US30Y": "^TYX",
}

_YAHOO_SUFFIXES = re.compile(r"\.(TO|V|L|HK|AX|NS|BO|SS|SZ|T)$", re.IGNORECASE)
_SAFE_TICKER = re.compile(r"^[A-Z0-9.\-^/=]+$", re.IGNORECASE)


def normalize_symbol(symbol: str) -> str:
    """Convert a broker symbol to Yahoo Finance format."""
    s = symbol.strip().upper()
    if s in _SYMBOL_MAP:
        return _SYMBOL_MAP[s]
    return s


def is_yahoo_safe(symbol: str) -> bool:
    """Check if the symbol contains path-traversal characters."""
    return bool(_SAFE_TICKER.match(symbol)) and ".." not in symbol and "/" not in symbol
