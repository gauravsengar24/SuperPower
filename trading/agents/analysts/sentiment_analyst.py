from __future__ import annotations

import logging
from datetime import datetime

from langchain_core.messages import HumanMessage

from trading.agents.schemas import SentimentReport
from trading.agents.utils.agent_utils import get_instrument_context_from_state, get_language_instruction

logger = logging.getLogger(__name__)


def run_sentiment_analyst(ticker, date, instrument, lang, llm, tool_nodes):
    tool_list = ", ".join(list(tool_nodes.keys())) if tool_nodes else "none"
    prompt = f"""Analyze social media and news sentiment for {ticker} around {date}.

{instrument}

Available tools: {tool_list}
Evaluate: social media buzz, news tone, retail sentiment, unusual options activity.
{lang}

Output your analysis as a structured report covering:
- Overall sentiment (bullish/bearish/neutral)
- Sentiment score (-1 to +1)
- Key signals driving sentiment
- Confidence (high/medium/low)
"""
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        text = result.content if hasattr(result, "content") else str(result)
        return SentimentReport(
            overall_sentiment="bullish" if "bullish" in text.lower() else "bearish" if "bearish" in text.lower() else "neutral",
            sentiment_score=_extract_score(text),
            key_signals=_extract_signals(text),
            confidence=_extract_confidence(text),
        )
    except Exception as e:
        logger.warning("Sentiment analysis error: %s", e)
        return SentimentReport(
            overall_sentiment="neutral",
            sentiment_score=0.0,
            key_signals=[],
            confidence="low",
        )


def _extract_score(text: str) -> float:
    import re
    scores = re.findall(r"(?:score|rating)[:\s]*(-?\d+\.?\d*)", text.lower())
    if scores:
        val = float(scores[0])
        return max(-1.0, min(1.0, val))
    if "strong buy" in text.lower() or "very bullish" in text.lower():
        return 0.8
    if "buy" in text.lower() or "bullish" in text.lower():
        return 0.4
    if "strong sell" in text.lower() or "very bearish" in text.lower():
        return -0.8
    if "sell" in text.lower() or "bearish" in text.lower():
        return -0.4
    return 0.0


def _extract_signals(text: str) -> list[str]:
    lines = [l.strip("-* ") for l in text.split("\n") if l.strip()]
    signals = [l for l in lines if any(k in l.lower() for k in ("signal", "key", "factor", "driver", "catalyst"))]
    return signals[:5] if signals else ["Sentiment analysis completed"]


def _extract_confidence(text: str) -> str:
    lower = text.lower()
    if "high confidence" in lower or "confidence: high" in lower:
        return "high"
    if "medium confidence" in lower or "confidence: medium" in lower:
        return "medium"
    if "low confidence" in lower or "confidence: low" in lower:
        return "low"
    return "medium"
