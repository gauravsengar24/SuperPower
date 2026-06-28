"""Yahoo Finance data functions."""

import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


def get_stock_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch OHLCV data from yfinance."""
    try:
        df = yf.download(symbol, start=start_date, end=end_date, progress=False)
        if df.empty:
            logger.warning("No data for %s %s-%s", symbol, start_date, end_date)
        return df
    except Exception as e:
        logger.warning("yfinance error for %s: %s", symbol, e)
        return pd.DataFrame()


def get_indicators(symbol: str, indicator: str, curr_date: str, look_back_days: int = 200) -> dict:
    """Compute technical indicators using stockstats."""
    try:
        from stockstats import StockDataFrame
        end = datetime.strptime(curr_date, "%Y-%m-%d")
        start = end - timedelta(days=look_back_days + 30)
        df = get_stock_data(symbol, start.strftime("%Y-%m-%d"), curr_date)
        if df.empty:
            return {"error": "No price data"}
        stock = StockDataFrame.retype(df.copy())
        indicators = [i.strip() for i in indicator.split(",")]
        result = {}
        for ind in indicators:
            try:
                result[ind] = stock[ind].iloc[-1]
            except Exception:
                result[ind] = None
        return result
    except Exception as e:
        return {"error": str(e)}


def get_fundamentals(symbol: str) -> dict:
    try:
        info = yf.Ticker(symbol).info or {}
        return {
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "eps": info.get("trailingEps"),
            "revenue": info.get("totalRevenue"),
            "profit_margins": info.get("profitMargins"),
            "debt_to_equity": info.get("debtToEquity"),
            "return_on_equity": info.get("returnOnEquity"),
            "beta": info.get("beta"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }
    except Exception as e:
        return {"error": str(e)}


def get_balance_sheet(symbol: str) -> dict:
    try:
        ticker = yf.Ticker(symbol)
        bs = ticker.balance_sheet
        if bs is None or bs.empty:
            return {}
        latest = bs.iloc[:, 0]
        return {k: v for k, v in latest.items()}
    except Exception:
        return {}


def get_cashflow(symbol: str) -> dict:
    try:
        ticker = yf.Ticker(symbol)
        cf = ticker.cashflow
        if cf is None or cf.empty:
            return {}
        latest = cf.iloc[:, 0]
        return {k: v for k, v in latest.items()}
    except Exception:
        return {}


def get_income_statement(symbol: str) -> dict:
    try:
        ticker = yf.Ticker(symbol)
        inc = ticker.income_stmt
        if inc is None or inc.empty:
            return {}
        latest = inc.iloc[:, 0]
        return {k: v for k, v in latest.items()}
    except Exception:
        return {}


def get_insider_transactions(symbol: str) -> list[dict]:
    try:
        ticker = yf.Ticker(symbol)
        insiders = ticker.insider_transactions
        if insiders is None or insiders.empty:
            return []
        return insiders.head(10).to_dict(orient="records")
    except Exception:
        return []
