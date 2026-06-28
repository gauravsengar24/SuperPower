"""Deterministic OHLCV snapshot — ground truth for agent price claims."""

import logging
from datetime import datetime, timedelta

import yfinance as yf

logger = logging.getLogger(__name__)


def build_verified_market_snapshot(symbol: str, curr_date: str) -> dict:
    """Fetch a verified OHLCV snapshot for the given symbol and date.

    Returns a dict with deterministic price data that agents can reference.
    """
    try:
        end = datetime.strptime(curr_date, "%Y-%m-%d")
        start = end - timedelta(days=365)
        df = yf.download(symbol, start=start.strftime("%Y-%m-%d"),
                         end=curr_date, progress=False)
        if df.empty:
            return {"symbol": symbol, "error": "No data available"}
        latest = df.iloc[-1]
        return {
            "symbol": symbol,
            "date": curr_date,
            "open": float(latest["Open"]),
            "high": float(latest["High"]),
            "low": float(latest["Low"]),
            "close": float(latest["Close"]),
            "volume": int(latest["Volume"]),
            "prev_close": float(df.iloc[-2]["Close"]) if len(df) > 1 else None,
            "data_points": len(df),
        }
    except Exception as e:
        logger.warning("Market snapshot error for %s: %s", symbol, e)
        return {"symbol": symbol, "error": str(e)}
