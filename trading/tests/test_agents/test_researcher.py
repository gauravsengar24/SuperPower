"""Tests for risk_researcher module."""

from trading.agents.researchers.risk_researcher import _parse_research_plan, _try_float


def test_parse_research_plan_long():
    text = "Direction: LONG\nEntry price: 150-155\nStop loss: 140\nTake profit: 170\nConfidence: HIGH"
    plan = _parse_research_plan("AAPL", text)
    assert plan.ticker == "AAPL"
    assert plan.direction == "LONG"
    assert plan.confidence == "HIGH"


def test_parse_research_plan_short():
    text = "Direction: SHORT\nEntry price: 200\nStop loss: 210\nTake profit: 180\nConfidence: MEDIUM"
    plan = _parse_research_plan("TSLA", text)
    assert plan.ticker == "TSLA"
    assert plan.direction == "SHORT"
    assert plan.confidence == "MEDIUM"


def test_parse_research_plan_neutral():
    plan = _parse_research_plan("SPY", "No clear direction, staying neutral")
    assert plan.direction == "NEUTRAL"
    assert plan.confidence == "MEDIUM"


def test_parse_research_plan_defaults():
    plan = _parse_research_plan("UNKNOWN", "")
    assert plan.ticker == "UNKNOWN"
    assert plan.direction == "NEUTRAL"
    assert plan.risk_factors == ["Market risk"]
    assert plan.catalysts == ["Earnings report"]


def test_try_float_with_number():
    assert _try_float("150.50") == 150.5
    assert _try_float("42") == 42.0


def test_try_float_no_number():
    assert _try_float("N/A") == 0.0
    assert _try_float("") == 0.0
