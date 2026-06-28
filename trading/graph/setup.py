"""Simple sequential analyst chain — runs analysts one at a time, aggregates reports."""

import logging
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from trading.agents.utils.agent_utils import get_instrument_context_from_state, get_language_instruction

logger = logging.getLogger(__name__)

# BUG FIX: Analyst names as constants
ANALYST_MARKET = "market"
ANALYST_SOCIAL = "social"
ANALYST_NEWS = "news"
ANALYST_FUNDAMENTALS = "fundamentals"


def run_simple_analyst_chain(state, selected_analysts, quick_llm, deep_llm, tool_nodes):
    """Run analysts in sequence, each building on previous reports."""
    trade_date = state.get("trade_date", datetime.now().strftime("%Y-%m-%d"))
    ticker = state.get("company_of_interest", "UNKNOWN")
    instrument = get_instrument_context_from_state(state)
    lang = get_language_instruction(state.get("config", {}))

    for analyst_key in selected_analysts:
        if analyst_key == ANALYST_MARKET:
            report = _run_market_analyst(ticker, trade_date, instrument, lang, quick_llm, tool_nodes)
            state["market_report"] = report
        elif analyst_key == ANALYST_SOCIAL:
            state["sentiment_report"] = f"Sentiment analysis for {ticker} — see full report below."
        elif analyst_key == ANALYST_NEWS:
            state["news_report"] = _run_news_analyst(ticker, trade_date, instrument, lang, quick_llm)
        elif analyst_key == ANALYST_FUNDAMENTALS:
            # BUG FIX: Fundamentals uses DEEP LLM for complex analysis
            state["fundamentals_report"] = _run_fundamentals_analyst(ticker, instrument, lang, deep_llm)

    state["final_trade_decision"] = _make_final_decision(state, ticker, lang, deep_llm)
    return state


def _run_market_analyst(ticker, date, instrument, lang, llm, tool_nodes):
    prompt = f"""Analyze market data for {ticker} on {date}.

{instrument}

Use the technical tools to fetch data and indicators.
Write a concise market analysis with price action, trends, and key levels.
{lang}"""
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        return f"Market analysis error: {e}"


def _run_news_analyst(ticker, date, instrument, lang, llm):
    prompt = f"""Analyze news and macro factors for {ticker} around {date}.

{instrument}

Consider: recent news, macro conditions, insider transactions.
{lang}"""
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        return f"News analysis error: {e}"


def _run_fundamentals_analyst(ticker, instrument, lang, llm):
    prompt = f"""Perform deep fundamental analysis of {ticker}.

{instrument}

Evaluate: financial health, growth metrics, valuation, competitive position.
This requires deep reasoning — take your time.
{lang}"""
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        return f"Fundamentals analysis error: {e}"


def _make_final_decision(state, ticker, lang, llm):
    mr = state.get("market_report", "")
    sr = state.get("sentiment_report", "")
    nr = state.get("news_report", "")
    fr = state.get("fundamentals_report", "")

    prompt = f"""Based on the following analysis for {ticker}, make a FINAL TRADE DECISION.

MARKET ANALYSIS:
{mr[:2000]}

SENTIMENT ANALYSIS:
{sr[:1000]}

NEWS ANALYSIS:
{nr[:2000]}

FUNDAMENTALS ANALYSIS:
{fr[:2000]}

Output exactly: STRONG BUY | BUY | HOLD | SELL | STRONG SELL
Then provide 1-2 sentence reasoning.
{lang}"""
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        return f"HOLD — Analysis error: {e}"
