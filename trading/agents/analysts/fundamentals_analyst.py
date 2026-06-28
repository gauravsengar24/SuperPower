from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage

from trading.agents.utils.agent_utils import get_instrument_context_from_state, get_language_instruction

logger = logging.getLogger(__name__)


def run_fundamentals_analyst(ticker, instrument, lang, llm):
    from trading.dataflows.world_bank import get_macro_economic_data
    macro = get_macro_economic_data(ticker, years=5)
    context = instrument + "\n\n" + macro if "No data" not in macro and "Could not" not in macro else instrument

    prompt = f"""Perform deep fundamental analysis of {ticker}.

{context}

This requires deep reasoning — take your time.
Evaluate the following in detail:

1. Financial Health: revenue trends, profit margins, debt-to-equity, cash flow
2. Growth Metrics: revenue growth, EPS growth, forward guidance
3. Valuation: P/E ratio (trailing + forward), P/B, PEG, EV/EBITDA
4. Competitive Position: market share, moat, industry trends
5. Risks: regulatory, competitive, operational, macroeconomic (use World Bank data above)

Provide a clear fundamental outlook: BULLISH / BEARISH / NEUTRAL
with supporting evidence for each point.
{lang}
"""
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        logger.warning("Fundamentals analysis error: %s", e)
        return f"Fundamentals analysis error for {ticker}: {e}"
