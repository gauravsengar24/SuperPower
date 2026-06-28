"""Tests for portfolio_manager module."""

from trading.agents.managers.portfolio_manager import _parse_portfolio_decision


def test_parse_approved():
    text = "APPROVED. This trade looks good. Risk: low volatility. Notes: proceed."
    decision = _parse_portfolio_decision(text)
    assert decision.approved is True
    assert decision.final_verdict == "APPROVED"


def test_parse_rejected():
    text = "REJECTED. Too risky given market conditions."
    decision = _parse_portfolio_decision(text)
    assert decision.approved is False
    assert decision.final_verdict == "REJECTED"


def test_parse_modified():
    text = "MODIFIED. Reduce position size by 50%. Approved with changes."
    decision = _parse_portfolio_decision(text)
    assert decision.approved is True
    assert decision.final_verdict == "MODIFIED"


def test_parse_default_rejected():
    decision = _parse_portfolio_decision("")
    assert decision.approved is False
    assert decision.final_verdict == "REJECTED"


def test_parse_with_risk_notes():
    text = "Risk notes: High volatility expected. Approved with caution."
    decision = _parse_portfolio_decision(text)
    assert "High volatility" in decision.risk_notes


def test_parse_with_size_modification():
    text = "Modification: Reduce to 50 shares. Risk: low. Approved."
    decision = _parse_portfolio_decision(text)
    assert decision.position_size_modification is not None
    assert "50" in decision.position_size_modification
