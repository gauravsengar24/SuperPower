"""Tests for risk_manager module."""

from trading.agents.schemas import TraderProposal
from trading.agents.risk_mgmt.risk_manager import run_risk_manager


def test_risk_manager_approves():
    prop = TraderProposal(
        ticker="AAPL", side="BUY", order_type="MARKET",
        quantity=10, confidence_score=0.8,
        reasoning="Good setup",
    )
    decision = run_risk_manager("AAPL", trader_proposal=prop)
    assert decision.final_verdict == "APPROVED" or decision.approved is True


def test_risk_manager_rejects_hold():
    prop = TraderProposal(
        ticker="AAPL", side="HOLD", order_type="MARKET",
        quantity=0, confidence_score=0.0, reasoning="No trade",
    )
    decision = run_risk_manager("AAPL", trader_proposal=prop)
    assert decision.final_verdict == "REJECTED"
    assert decision.approved is False


def test_risk_manager_blocks_overpositioned():
    prop = TraderProposal(
        ticker="GOOGL", side="BUY", order_type="MARKET",
        quantity=1000, limit_price=500.0, confidence_score=0.9,
        reasoning="Strong buy",
    )
    decision = run_risk_manager(
        "GOOGL", trader_proposal=prop,
        aegis_config={"max_positions": 1},
    )
    # Should be rejected by position limit since estimated_value is large
    assert decision.final_verdict == "REJECTED" or not decision.approved


def test_risk_manager_no_proposal():
    decision = run_risk_manager("AAPL", trader_proposal=None)
    assert decision.final_verdict == "REJECTED"
    assert decision.approved is False
