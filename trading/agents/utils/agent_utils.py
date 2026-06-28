"""Central hub: re-exports data tools, resolves instrument identity, builds context strings."""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import Command

from trading.agents.utils.agent_states import AgentState

logger = logging.getLogger(__name__)


def get_language_instruction(config: dict) -> str:
    lang = config.get("output_language", "English")
    if lang.lower() == "english":
        return ""
    return (
        f"\nIMPORTANT: All your responses MUST be written in {lang}. "
        f"This is a strict requirement. Your answer will be rejected "
        f"if you write in any other language."
    )


def resolve_instrument_identity(ticker: str) -> dict:
    import yfinance as yf
    try:
        info = yf.Ticker(ticker).info or {}
        return {
            "long_name": info.get("longName", info.get("shortName", ticker)),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
            "market_cap": info.get("marketCap", 0),
            "currency": info.get("currency", "USD"),
            "exchange": info.get("exchange", "N/A"),
            "country": info.get("country", "N/A"),
        }
    except Exception as e:
        logger.warning("Could not resolve identity for %s: %s", ticker, e)
        return {"long_name": ticker, "sector": "N/A", "industry": "N/A"}


def build_instrument_context(ticker: str, asset_type: str, identity: dict) -> str:
    if asset_type == "crypto":
        return f"Cryptocurrency: {ticker}"
    return (
        f"Company: {identity.get('long_name', ticker)} ({ticker})\n"
        f"Sector: {identity.get('sector', 'N/A')} | "
        f"Industry: {identity.get('industry', 'N/A')}\n"
        f"Exchange: {identity.get('exchange', 'N/A')} | "
        f"Country: {identity.get('country', 'N/A')}\n"
        f"Currency: {identity.get('currency', 'USD')}"
    )


def get_instrument_context_from_state(state: AgentState) -> str:
    return state.get("instrument_context", "No instrument context available.")


def create_msg_delete() -> Callable:
    name = "delete_messages"
    cache_key = f"_{name}_last_msg"

    def node(state: AgentState) -> dict:
        msgs = state.get("messages", [])
        if len(msgs) > 2:
            return {"messages": [msgs[0], msgs[-1]]}
        return {"messages": msgs}

    node.__name__ = name
    return node


def create_tool_node_with_fallback(tools: list) -> Any:
    from langgraph.prebuilt import ToolNode
    return ToolNode(tools)
