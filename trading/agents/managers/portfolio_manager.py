from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage

from trading.agents.schemas import PortfolioDecision
from trading.agents.utils.agent_utils import get_instrument_context_from_state, get_language_instruction

logger = logging.getLogger(__name__)


def run_portfolio_manager(ticker, instrument, lang, llm, research_plan=None,
                          trader_proposal=None, market_report="", news_report="",
                          fundamentals_report=""):
    plan_str = ""
    if research_plan:
        plan_str = f"Direction: {research_plan.direction}\nConfidence: {research_plan.confidence}\n"
    proposal_str = ""
    if trader_proposal:
        proposal_str = (
            f"Side: {trader_proposal.side}\n"
            f"Order: {trader_proposal.quantity} @ {trader_proposal.order_type}\n"
            f"Confidence: {trader_proposal.confidence_score:.2f}\n"
        )

    prompt = f"""Review the trade proposal for {ticker} and make a final portfolio decision.

{instrument}

RESEARCH PLAN:
{plan_str}

TRADE PROPOSAL:
{proposal_str}

MARKET: {market_report[:1000]}
NEWS: {news_report[:1000]}
FUNDAMENTALS: {fundamentals_report[:1000]}

Approve or reject. If modifying, specify changes.
Provide risk notes and final verdict: APPROVED / REJECTED / MODIFIED.
{lang}
"""
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        text = result.content if hasattr(result, "content") else str(result)
        return _parse_portfolio_decision(text)
    except Exception as e:
        logger.warning("Portfolio manager error: %s", e)
        return PortfolioDecision(
            approved=False, risk_notes=f"Error: {e}",
            final_verdict="REJECTED",
        )


def _parse_portfolio_decision(text: str) -> PortfolioDecision:
    lower = text.lower()
    modified = "modif" in lower
    approved = "approve" in lower or "approved" in lower
    rejected = "reject" in lower or "rejected" in lower

    if modified:
        final_verdict = "MODIFIED"
        approved = True
    elif rejected:
        final_verdict = "REJECTED"
        approved = False
    elif approved:
        final_verdict = "APPROVED"
    else:
        final_verdict = "REJECTED"
        approved = False

    import re
    notes_match = re.search(r"(?:risk notes?|notes?)[:\s]*(.+?)(?:\n|$)", text, re.IGNORECASE)
    risk_notes = notes_match.group(1).strip() if notes_match else text[:200]

    size_match = re.search(r"(?:size|modif|change)[:\s]*(.+?)(?:\n|$)", text, re.IGNORECASE)
    position_size_modification = size_match.group(1).strip() if size_match else None

    return PortfolioDecision(
        approved=approved,
        position_size_modification=position_size_modification,
        risk_notes=risk_notes,
        final_verdict=final_verdict,
    )
