from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.types import Command

from trading.agents.utils.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
)

logger = logging.getLogger(__name__)

MARKET_ANALYST_PROMPT = """You are a Market/Technical Analyst at a trading firm.
Your role is to analyze market data and technical indicators for {instrument_context}.

Today's date: {current_date}
Analysis date: {trade_date}

You have access to the following tools:
- get_stock_data(symbol, start_date, end_date) — Fetch OHLCV price data
- get_indicators(symbol, indicator, curr_date, look_back_days) — Technical indicators
- get_verified_market_snapshot(symbol, curr_date) — Deterministic ground-truth OHLCV snapshot

IMPORTANT: You MUST call get_verified_market_snapshot first to anchor your analysis
in real data. Then use get_stock_data and get_indicators for deeper analysis.

Available indicators: sma (20,50,200), ema (12,26), rsi (14), macd, bb (20,2),
atr (14), obv, volume, volatility, momentum, roc, williams_r, cci, adx, stoch.

Write a comprehensive market analysis report covering:
1. Price action and trends
2. Key support/resistance levels
3. Technical indicator signals
4. Volume analysis
5. Overall technical outlook (bullish/bearish/neutral)
6. Key risks and opportunities

{language_instruction}
"""


def create_market_analyst(llm: Any):
    prompt = ChatPromptTemplate.from_messages([
        ("system", MARKET_ANALYST_PROMPT),
        MessagesPlaceholder(variable_name="messages"),
    ])

    def analyst_node(state: dict) -> Command:
        trade_date = state.get("trade_date", datetime.now().strftime("%Y-%m-%d"))
        instrument_context = get_instrument_context_from_state(state)
        lang_instruction = get_language_instruction(state.get("config", {}))

        chain = prompt.partial(
            instrument_context=instrument_context,
            current_date=datetime.now().strftime("%Y-%m-%d"),
            trade_date=trade_date,
            language_instruction=lang_instruction,
        )

        bound = chain | llm.bind_tools([
            _get_stock_data,
            _get_indicators,
            _get_verified_snapshot,
        ])

        result = bound.invoke({"messages": state.get("messages", [])})
        return Command(
            goto="market_tools",
            update={"messages": [result], "market_report": result.content if hasattr(result, "content") else str(result)},
        )

    return analyst_node


def run_market_analyst(ticker, date, instrument, lang, llm, tool_nodes):
    """Simple market analyst call (not a LangGraph node)."""
    tool_list = ", ".join(list(tool_nodes.keys())) if tool_nodes else "none"
    prompt = f"""Analyze market data for {ticker} on {date}.

{instrument}

Available tools: {tool_list}
Use the technical tools to fetch data and indicators.
Write a concise market analysis with price action, trends, and key levels.
{lang}"""
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        return f"Market analysis error: {e}"


def _get_stock_data(symbol: str, start_date: str, end_date: str) -> str:
    from trading.dataflows.y_finance import get_stock_data
    return str(get_stock_data(symbol, start_date, end_date))


def _get_indicators(symbol: str, indicator: str, curr_date: str, look_back_days: int = 200) -> str:
    from trading.dataflows.y_finance import get_indicators
    return str(get_indicators(symbol, indicator, curr_date, look_back_days))


def _get_verified_snapshot(symbol: str, curr_date: str) -> str:
    from trading.dataflows.market_data_validator import build_verified_market_snapshot
    return str(build_verified_market_snapshot(symbol, curr_date))
