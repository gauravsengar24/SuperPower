from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage

from trading.agents.schemas import ResearchPlan
from trading.agents.utils.agent_utils import get_instrument_context_from_state, get_language_instruction

logger = logging.getLogger(__name__)


def run_researcher(ticker, instrument, lang, llm, market_report="", sentiment_report="",
                   news_report="", fundamentals_report=""):
    prompt = f"""Create a detailed research plan for {ticker} based on the analysis below.

{instrument}

MARKET ANALYSIS:
{market_report[:2000]}

SENTIMENT ANALYSIS:
{sentiment_report[:1000]}

NEWS ANALYSIS:
{news_report[:2000]}

FUNDAMENTALS ANALYSIS:
{fundamentals_report[:2000]}

Produce a structured research plan with:
- Trading direction: LONG / SHORT / NEUTRAL
- Entry price range
- Stop loss level
- Take profit level
- Confidence: HIGH / MEDIUM / LOW
- Detailed reasoning
- Key risk factors (list 3-5)
- Potential catalysts (list 2-3)
{lang}
"""
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        text = result.content if hasattr(result, "content") else str(result)
        return _parse_research_plan(ticker, text)
    except Exception as e:
        logger.warning("Researcher error: %s", e)
        return ResearchPlan(
            ticker=ticker, direction="NEUTRAL", entry_price_range="N/A",
            stop_loss=0.0, take_profit=0.0, confidence="LOW",
            reasoning=f"Research error: {e}", risk_factors=[], catalysts=[],
        )


def _parse_research_plan(ticker: str, text: str) -> ResearchPlan:
    lower = text.lower()
    if "long" in lower and "short" not in lower:
        direction = "LONG"
    elif "short" in lower and "long" not in lower:
        direction = "SHORT"
    else:
        direction = "NEUTRAL"

    import re
    def extract(label, default=""):
        m = re.search(rf"{label}[:\s]*(.+?)(?:\n|$)", text, re.IGNORECASE)
        return m.group(1).strip() if m else default

    confidence = extract("confidence", "MEDIUM").upper()
    if confidence not in ("HIGH", "MEDIUM", "LOW"):
        confidence = "MEDIUM"

    risk_factors = [l.strip("-* ") for l in text.split("\n")
                    if l.strip() and any(k in l.lower() for k in ("risk",))
                    and not l.lower().startswith(("entry", "stop", "take", "confid"))]
    catalysts = [l.strip("-* ") for l in text.split("\n")
                 if l.strip() and any(k in l.lower() for k in ("catalyst", "catalysts"))]

    return ResearchPlan(
        ticker=ticker, direction=direction,
        entry_price_range=extract("entry price", "N/A"),
        stop_loss=_try_float(extract("stop loss", "0")),
        take_profit=_try_float(extract("take profit", "0")),
        confidence=confidence,
        reasoning=text[:500],
        risk_factors=risk_factors[:5] or ["Market risk"],
        catalysts=catalysts[:3] or ["Earnings report"],
    )


def _try_float(s: str) -> float:
    import re
    m = re.search(r"[\d.]+", s)
    return float(m.group()) if m else 0.0
