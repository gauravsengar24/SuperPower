from __future__ import annotations

"""Agent state TypedDicts for the LangGraph pipeline."""

from typing import Any, Sequence

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict


class InvestDebateState(TypedDict, total=False):
    bull_history: str
    bear_history: str
    history: str
    current_response: str
    judge_decision: str
    generation: int


class RiskDebateState(TypedDict, total=False):
    aggressive_history: str
    conservative_history: str
    neutral_history: str
    history: str
    judge_decision: str
    generation: int


class AgentState(TypedDict, total=False):
    company_of_interest: str
    trade_date: str
    asset_type: str
    past_context: str
    instrument_context: str

    messages: Sequence[BaseMessage]

    market_report: str
    sentiment_report: str
    news_report: str
    fundamentals_report: str

    investment_debate_state: InvestDebateState
    risk_debate_state: RiskDebateState

    investment_plan: Any
    trader_investment_plan: str
    final_trade_decision: str
