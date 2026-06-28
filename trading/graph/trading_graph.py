"""Main orchestrator — TradingAgentsGraph with bug fixes applied."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yfinance as yf
from langgraph.prebuilt import ToolNode

from trading.agents.utils.agent_utils import (
    build_instrument_context,
    resolve_instrument_identity,
    create_msg_delete,
)
from trading.agents.utils.memory import TradingMemoryLog
from trading.agents.utils.signal import SignalProcessor
from trading.agents.utils.agent_states import AgentState
from trading.dataflows.config import set_config
from trading.dataflows.symbol_utils import safe_ticker_component
from trading.default_config import DEFAULT_CONFIG
from trading.llm_clients import create_llm_client
from trading.dataflows.y_finance import (
    get_stock_data,
    get_indicators,
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_insider_transactions,
)
from trading.dataflows.yfinance_news import get_news, get_global_news
from trading.reporting import write_report_tree

logger = logging.getLogger(__name__)

# BUG FIX: Analyst keys as constants to prevent magic strings
ANALYST_MARKET = "market"
ANALYST_SOCIAL = "social"
ANALYST_NEWS = "news"
ANALYST_FUNDAMENTALS = "fundamentals"


def _get_macro_indicators(*args, **kwargs):
    """Fetch macro-economic indicators for the given context."""
    return "Macro indicators data — coming in Phase 5"


def _get_prediction_markets(*args, **kwargs):
    """Fetch prediction market data (Polymarket) for the given ticker."""
    return "Prediction markets data — coming in Phase 5"


def _get_verified_market_snapshot(symbol, curr_date):
    """Fetch the deterministic verified OHLCV snapshot for ground truth."""
    from trading.dataflows.market_data_validator import build_verified_market_snapshot
    return str(build_verified_market_snapshot(symbol, curr_date))


class TradingAgentsGraph:
    def __init__(self, selected_analysts=("market", "social", "news", "fundamentals"),
                 debug=False, config=None, callbacks=None):
        self.debug = debug
        self.config = config or DEFAULT_CONFIG
        self.callbacks = callbacks or []
        set_config(self.config)

        Path(self.config["results_dir"]).mkdir(parents=True, exist_ok=True)
        Path(self.config["data_cache_dir"]).mkdir(parents=True, exist_ok=True)

        self._llm_kwargs = self._get_provider_kwargs()
        if self.callbacks:
            self._llm_kwargs["callbacks"] = self.callbacks

        self._deep_client = create_llm_client(
            provider=self.config["llm_provider"],
            model=self.config["deep_think_llm"],
            base_url=self.config.get("backend_url"),
            **self._llm_kwargs,
        )
        self._quick_client = create_llm_client(
            provider=self.config["llm_provider"],
            model=self.config["quick_think_llm"],
            base_url=self.config.get("backend_url"),
            **self._llm_kwargs,
        )

        self.memory_log = TradingMemoryLog(self.config)
        self.tool_nodes = self._create_tool_nodes()
        self.signal_processor = SignalProcessor()
        self.curr_state = None
        self.ticker = None
        self.selected_analysts = selected_analysts

    def _get_deep_llm(self):
        return self._deep_client.get_llm()

    def _get_quick_llm(self):
        return self._quick_client.get_llm()

    def _get_provider_kwargs(self):
        kwargs = {}
        provider = self.config.get("llm_provider", "").lower()
        if provider == "google":
            if self.config.get("google_thinking_level"):
                kwargs["thinking_level"] = self.config["google_thinking_level"]
        elif provider == "openai":
            if self.config.get("openai_reasoning_effort"):
                kwargs["reasoning_effort"] = self.config["openai_reasoning_effort"]
        elif provider == "anthropic":
            if self.config.get("anthropic_effort"):
                kwargs["effort"] = self.config["anthropic_effort"]
        if self.config.get("temperature") is not None:
            kwargs["temperature"] = float(self.config["temperature"])
        return kwargs

    def _create_tool_nodes(self):
        return {
            ANALYST_MARKET: ToolNode([
                get_stock_data,
                get_indicators,
                _get_verified_market_snapshot,
            ]),
            # BUG FIX: Social ToolNode only includes tools the sentiment agent actually uses
            ANALYST_SOCIAL: ToolNode([get_news]),
            ANALYST_NEWS: ToolNode([
                get_news,
                get_global_news,
                get_insider_transactions,
                _get_macro_indicators,
                _get_prediction_markets,
            ]),
            ANALYST_FUNDAMENTALS: ToolNode([
                get_fundamentals,
                get_balance_sheet,
                get_cashflow,
                get_income_statement,
            ]),
        }

    def propagate(self, ticker, date, asset_type="stock"):
        from trading.graph.propagation import create_initial_state
        from langgraph.graph import StateGraph, END, START

        self.ticker = ticker
        instrument_context = self._resolve_instrument_context(ticker, asset_type)
        past_context = self.memory_log.get_past_context(ticker)

        init = create_initial_state(ticker, date, asset_type, past_context, instrument_context)

        workflow = StateGraph(AgentState)
        workflow.add_node("analyst", self._run_analysts)
        workflow.add_edge(START, "analyst")
        workflow.add_node("end_node", lambda s: s)
        workflow.add_edge("analyst", "end_node")
        workflow.add_edge("end_node", END)
        graph = workflow.compile()

        final = graph.invoke(init)
        self.curr_state = final
        self.memory_log.store_decision(ticker, date, final.get("final_trade_decision", "HOLD"))
        signal = self.signal_processor.process_signal(final.get("final_trade_decision", "HOLD"))
        return final, signal

    def _resolve_instrument_context(self, ticker, asset_type):
        identity = resolve_instrument_identity(ticker)
        return build_instrument_context(ticker, asset_type, identity)

    def _run_analysts(self, state):
        from trading.graph.setup import run_simple_analyst_chain
        return run_simple_analyst_chain(
            state, self.selected_analysts,
            self._get_quick_llm(), self._get_deep_llm(),
            self.tool_nodes,
        )

    def save_reports(self, final_state, ticker, save_path=None):
        if save_path is None:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe = safe_ticker_component(ticker)
            save_path = Path(self.config["results_dir"]) / "reports" / f"{safe}_{stamp}"
        return write_report_tree(final_state, ticker, save_path)

    def process_signal(self, raw):
        return self.signal_processor.process_signal(raw)
