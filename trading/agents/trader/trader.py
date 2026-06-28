from __future__ import annotations

import logging
from typing import Optional

from langchain_core.messages import HumanMessage

from trading.agents.schemas import TraderProposal
from trading.agents.utils.agent_utils import get_instrument_context_from_state, get_language_instruction

logger = logging.getLogger(__name__)


def run_trader(ticker, instrument, lang, llm, research_plan=None,
               market_report="", sentiment_report=""):
    plan_str = ""
    if research_plan:
        plan_str = (
            f"\nRESEARCH PLAN:\n"
            f"Direction: {research_plan.direction}\n"
            f"Entry: {research_plan.entry_price_range}\n"
            f"Stop Loss: {research_plan.stop_loss}\n"
            f"Take Profit: {research_plan.take_profit}\n"
            f"Confidence: {research_plan.confidence}\n"
        )

    prompt = f"""Based on the research plan and analysis for {ticker}, create a trade proposal.

{instrument}{plan_str}

MARKET ANALYSIS:
{market_report[:1500]}

SENTIMENT:
{sentiment_report[:1000]}

Output a structured trade proposal with:
- Side: BUY or SELL
- Order type: MARKET, LIMIT, or STOP
- Quantity (number of shares)
- Limit price (if applicable)
- Stop price (if applicable)
- Confidence score (0.0 to 1.0)
- Detailed reasoning
{lang}
"""
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        text = result.content if hasattr(result, "content") else str(result)
        return _parse_trader_proposal(ticker, text)
    except Exception as e:
        logger.warning("Trader error: %s", e)
        return TraderProposal(
            ticker=ticker, side="HOLD", order_type="MARKET",
            quantity=0, confidence_score=0.0,
            reasoning=f"Trader error: {e}",
        )


def _parse_trader_proposal(ticker: str, text: str) -> TraderProposal:
    lower = text.lower()
    side = "BUY" if "buy" in lower and "sell" not in lower[:lower.find("buy")+10] else "SELL" if "sell" in lower else "HOLD"
    order_type = "LIMIT" if "limit" in lower else "STOP" if "stop" in lower else "MARKET"

    import re
    def extract(label, default=None):
        m = re.search(rf"{label}[:\s]*([\d.]+)", text, re.IGNORECASE)
        return float(m.group(1)) if m else default

    qty_match = re.search(r"(?:quantity|qty)[:\s]*(\d+)", text, re.IGNORECASE)
    quantity = int(qty_match.group(1)) if qty_match else 100

    conf_match = re.search(r"(?:confidence|score)[:\s]*(-?[\d.]+)", text, re.IGNORECASE)
    confidence = max(0.0, min(1.0, float(conf_match.group(1)))) if conf_match else 0.5

    return TraderProposal(
        ticker=ticker, side=side, order_type=order_type,
        quantity=quantity,
        limit_price=extract("limit price"),
        stop_price=extract("stop price"),
        confidence_score=confidence,
        reasoning=text[:500],
    )
