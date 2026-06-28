from __future__ import annotations

import logging
from datetime import datetime

from langchain_core.messages import HumanMessage

from trading.agents.utils.agent_utils import get_instrument_context_from_state, get_language_instruction

logger = logging.getLogger(__name__)


def run_news_analyst(ticker, date, instrument, lang, llm):
    prompt = f"""Analyze news and macro factors for {ticker} around {date}.

{instrument}

Consider: recent news, macro conditions, insider transactions.
{lang}

Provide a structured analysis covering:
1. Recent news headlines and their market impact
2. Macro-economic factors affecting the stock
3. Insider transaction patterns
4. Overall news sentiment (positive/negative/neutral)
5. Key catalysts to watch
"""
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        logger.warning("News analysis error: %s", e)
        return f"News analysis error for {ticker}: {e}"
