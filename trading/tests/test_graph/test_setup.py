"""Tests for graph/setup.py pipeline orchestration."""

from unittest.mock import MagicMock

from trading.graph.setup import run_simple_analyst_chain, ANALYST_MARKET, ANALYST_SOCIAL, ANALYST_NEWS, ANALYST_FUNDAMENTALS
from trading.graph.propagation import create_initial_state
from trading.default_config import DEFAULT_CONFIG


def _make_llm(response_text="BUY AAPL — strong setup"):
    llm = MagicMock()
    result = MagicMock()
    result.content = response_text
    llm.invoke.return_value = result
    return llm


def test_chain_all_analysts():
    state = create_initial_state("AAPL", "2026-06-29")
    state["config"] = DEFAULT_CONFIG.copy()
    quick = _make_llm("Market looks strong")
    deep = _make_llm("Direction: LONG\nEntry price: 180-185\nConfidence: HIGH")

    result = run_simple_analyst_chain(
        state, (ANALYST_MARKET, ANALYST_SOCIAL, ANALYST_NEWS, ANALYST_FUNDAMENTALS),
        quick, deep, {},
    )
    assert "market_report" in result
    assert "sentiment_report" in result
    assert "news_report" in result
    assert "fundamentals_report" in result
    assert "investment_plan" in result
    assert "trader_investment_plan" in result
    assert "final_trade_decision" in result


def test_chain_market_only():
    state = create_initial_state("AAPL", "2026-06-29")
    state["config"] = DEFAULT_CONFIG.copy()
    quick = _make_llm("Market is trending up")
    deep = _make_llm("Direction: LONG\nConfidence: HIGH")

    result = run_simple_analyst_chain(
        state, (ANALYST_MARKET,), quick, deep, {},
    )
    assert result["market_report"]
    assert result["sentiment_report"] == ""


def test_chain_handles_llm_error():
    state = create_initial_state("AAPL", "2026-06-29")
    state["config"] = DEFAULT_CONFIG.copy()
    quick = MagicMock()
    quick.invoke.side_effect = Exception("API error")
    deep = MagicMock()
    deep.invoke.side_effect = Exception("API error")

    result = run_simple_analyst_chain(
        state, (ANALYST_MARKET, ANALYST_SOCIAL), quick, deep, {},
    )
    assert "error" in result.get("market_report", "").lower() or result.get("market_report", "")
    assert result["final_trade_decision"] in ("APPROVED", "REJECTED")


def test_chain_state_preserved():
    state = create_initial_state("TSLA", "2026-01-15")
    state["config"] = DEFAULT_CONFIG.copy()
    state["custom_field"] = "should survive"
    quick = _make_llm("Neutral")
    deep = _make_llm("Direction: NEUTRAL\nConfidence: LOW")

    result = run_simple_analyst_chain(
        state, (ANALYST_MARKET, ANALYST_SOCIAL), quick, deep, {},
    )
    assert result["company_of_interest"] == "TSLA"
    assert result["trade_date"] == "2026-01-15"
    assert result.get("custom_field") == "should survive"


def test_chain_empty_analysts():
    state = create_initial_state("AAPL", "2026-06-29")
    state["config"] = DEFAULT_CONFIG.copy()
    quick = _make_llm("N/A")
    deep = _make_llm("Direction: NEUTRAL")

    result = run_simple_analyst_chain(state, (), quick, deep, {})
    assert result["final_trade_decision"] in ("APPROVED", "REJECTED")


def test_chain_research_plan_created():
    state = create_initial_state("AAPL", "2026-06-29")
    state["config"] = DEFAULT_CONFIG.copy()
    state["market_report"] = "Strong uptrend with increasing volume"
    state["sentiment_report"] = "Bullish sentiment"
    state["news_report"] = "Positive earnings news"
    state["fundamentals_report"] = "Solid financials"
    quick = _make_llm("Buy signal confirmed")
    deep = _make_llm("Direction: LONG\nEntry price: 180-185\nConfidence: HIGH")

    result = run_simple_analyst_chain(state, (ANALYST_MARKET,), quick, deep, {})
    plan = result.get("investment_plan")
    assert plan is not None
    assert hasattr(plan, "direction")
    assert hasattr(plan, "confidence")
