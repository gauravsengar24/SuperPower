"""Bull/Bear debate researcher — TradingAgents-parity debate system.

Two LLM agents argue opposite sides (bull vs bear) then a judge
synthesizes a final ResearchPlan from the debate.
"""

import logging
import re

from langchain_core.messages import HumanMessage

from trading.agents.schemas import ResearchPlan

logger = logging.getLogger(__name__)


def run_debate_researcher(ticker, instrument, lang, deep_llm, quick_llm,
                           market_report="", sentiment_report="",
                           news_report="", fundamentals_report="",
                           max_rounds: int = 1):
    context = f"{instrument}\n\nMARKET ANALYSIS:\n{market_report[:2000]}\n\nSENTIMENT:\n{sentiment_report[:1000]}\n\nNEWS:\n{news_report[:2000]}\n\nFUNDAMENTALS:\n{fundamentals_report[:2000]}"

    bull = _generate_bull_case(ticker, context, lang, deep_llm)
    bear = _generate_bear_case(ticker, context, lang, deep_llm)

    if max_rounds > 1:
        for r in range(1, max_rounds):
            bull = _rebuttal(ticker, "bull", bull, bear, context, lang, quick_llm, r)
            bear = _rebuttal(ticker, "bear", bear, bull, context, lang, quick_llm, r)

    plan = _judge_decision(ticker, context, bull, bear, lang, deep_llm)
    return plan


def _generate_bull_case(ticker, context, lang, llm):
    prompt = (
        f"You are a BULLISH analyst arguing FOR taking a long position in {ticker}.\n\n"
        f"{context}\n\n"
        f"Build your case: why should we BUY {ticker}? Focus on:\n"
        f"- Positive technical signals\n"
        f"- Bullish sentiment drivers\n"
        f"- Favorable fundamentals\n"
        f"- Upcoming catalysts\n"
        f"- Key price targets and stop-loss levels\n"
        f"Be specific and data-driven.\n"
        f"{lang}"
    )
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        logger.warning("Bull researcher error: %s", e)
        return f"Bull case unavailable: {e}"


def _generate_bear_case(ticker, context, lang, llm):
    prompt = (
        f"You are a BEARISH analyst arguing AGAINST taking a long position in {ticker}.\n\n"
        f"{context}\n\n"
        f"Build your case: why should we SELL or AVOID {ticker}? Focus on:\n"
        f"- Negative technical signals\n"
        f"- Bearish sentiment drivers\n"
        f"- Fundamental risks\n"
        f"- Downside catalysts\n"
        f"- Key risk factors and support levels\n"
        f"Be specific and data-driven.\n"
        f"{lang}"
    )
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        logger.warning("Bear researcher error: %s", e)
        return f"Bear case unavailable: {e}"


def _rebuttal(ticker, side, own_case, opposing_case, context, lang, llm, round_num):
    prompt = (
        f"You are a {side.upper()} analyst arguing about {ticker} (round {round_num}).\n\n"
        f"Your case:\n{own_case[:1500]}\n\n"
        f"The opposing case:\n{opposing_case[:1500]}\n\n"
        f"Rebuttal: address the opposing arguments and strengthen your case.\n"
        f"{lang}"
    )
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        logger.warning("Rebuttal error: %s", e)
        return own_case


def _judge_decision(ticker, context, bull_case, bear_case, lang, llm):
    prompt = (
        f"You are a senior judge evaluating the bull vs bear debate for {ticker}.\n\n"
        f"CONTEXT:\n{context[:1000]}\n\n"
        f"BULL CASE:\n{bull_case[:2000]}\n\n"
        f"BEAR CASE:\n{bear_case[:2000]}\n\n"
        f"Evaluate both arguments critically and produce a structured research plan with:\n"
        f"- Trading direction: LONG / SHORT / NEUTRAL\n"
        f"- Entry price range\n"
        f"- Stop loss level\n"
        f"- Take profit level\n"
        f"- Confidence: HIGH / MEDIUM / LOW\n"
        f"- Detailed reasoning (synthesizing both sides)\n"
        f"- Key risk factors (list 3-5)\n"
        f"- Potential catalysts (list 2-3)\n"
        f"{lang}"
    )
    try:
        result = llm.invoke([HumanMessage(content=prompt)])
        text = result.content if hasattr(result, "content") else str(result)
        return _parse_judge_plan(ticker, text)
    except Exception as e:
        logger.warning("Judge error: %s", e)
        return ResearchPlan(
            ticker=ticker, direction="NEUTRAL", entry_price_range="N/A",
            stop_loss=0.0, take_profit=0.0, confidence="LOW",
            reasoning=f"Judge error: {e}", risk_factors=[], catalysts=[],
        )


def _parse_judge_plan(ticker, text):
    lower = text.lower()
    long_score = lower.count("long") + lower.count("buy") + lower.count("bull")
    short_score = lower.count("short") + lower.count("sell") + lower.count("bear")
    if long_score > short_score + 1:
        direction = "LONG"
    elif short_score > long_score + 1:
        direction = "SHORT"
    else:
        direction = "NEUTRAL"

    def extract(label, default=""):
        m = re.search(rf"{label}[:\s]*(.+?)(?:\n|$)", text, re.IGNORECASE)
        return m.group(1).strip() if m else default

    confidence = extract("confidence", "MEDIUM").upper()
    if confidence not in ("HIGH", "MEDIUM", "LOW"):
        confidence = "MEDIUM"

    lines = text.split("\n")
    risk_factors = [
        ln.strip("-* ").strip("\"'") for ln in lines
        if ln.strip() and any(k in ln.lower() for k in ("risk",))
    ][:5] or ["Market risk"]

    catalysts = [
        ln.strip("-* ").strip("\"'") for ln in lines
        if ln.strip() and any(k in ln.lower() for k in ("catalyst",))
    ][:3] or ["Earnings report"]

    return ResearchPlan(
        ticker=ticker, direction=direction,
        entry_price_range=extract("entry price", "N/A"),
        stop_loss=_try_float(extract("stop loss", "0")),
        take_profit=_try_float(extract("take profit", "0")),
        confidence=confidence,
        reasoning=text[:500],
        risk_factors=risk_factors,
        catalysts=catalysts,
    )


def _try_float(s: str) -> float:
    m = re.search(r"[\d.]+", s)
    return float(m.group()) if m else 0.0
