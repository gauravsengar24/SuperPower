"""Tests for A.E.G.I.S. risk gate system."""

import pytest
from trading.risk.aegis import (
    AEGIS, TradeProposal, PortfolioState, Position, MarketSnapshot,
    GateDecision,
)


@pytest.fixture
def portfolio():
    return PortfolioState(
        positions=[
            Position("AAPL", 100, 150.0, 155.0, pnl=500.0, pnl_pct=0.033),
            Position("MSFT", 50, 300.0, 310.0, pnl=500.0, pnl_pct=0.033),
        ],
        cash=50000.0,
        total_value=100000.0,
        peak_value=105000.0,
        daily_start_value=101000.0,
        initial_value=100000.0,
    )


@pytest.fixture
def market():
    return MarketSnapshot(ticker="GOOGL", price=180.0, vix=15.0, atr=3.0)


@pytest.fixture
def proposal():
    return TradeProposal(ticker="GOOGL", side="buy", qty=10,
                         order_type="market", estimated_value=1800.0,
                         confidence=0.8)


class TestPositionLimitGate:
    def test_under_limit_passes(self, proposal, portfolio, market):
        aegis = AEGIS({"max_positions": 10, "max_position_pct": 0.25})
        passed, results = aegis.check(proposal, portfolio, market)
        assert passed

    def test_over_positions_rejected(self, proposal, portfolio, market):
        portfolio.positions = [Position(f"TICKER{i}", 100, 100, 100) for i in range(10)]
        aegis = AEGIS({"max_positions": 5})
        passed, results = aegis.check(proposal, portfolio, market)
        assert not passed
        assert any(r.gate_name == "position_limit" and r.decision == GateDecision.REJECT
                   for r in results)


class TestDrawdownGate:
    def test_daily_drawdown_rejected(self, proposal, portfolio, market):
        portfolio.daily_start_value = portfolio.total_value * 1.1
        aegis = AEGIS({"max_daily_drawdown": 0.05})
        passed, results = aegis.check(proposal, portfolio, market)
        assert not passed

    def test_trailing_drawdown_rejected(self, proposal, portfolio, market):
        portfolio.peak_value = portfolio.total_value * 1.2
        aegis = AEGIS({"max_trailing_drawdown": 0.10})
        passed, results = aegis.check(proposal, portfolio, market)
        assert not passed


class TestVolatilityFilterGate:
    def test_high_vix_rejected(self, proposal, portfolio, market):
        market.vix = 50.0
        aegis = AEGIS({"volatility_threshold": 0.30})
        passed, results = aegis.check(proposal, portfolio, market)
        assert not passed

    def test_normal_vix_passes(self, proposal, portfolio, market):
        market.vix = 15.0
        aegis = AEGIS({"volatility_threshold": 0.40})
        passed, results = aegis.check(proposal, portfolio, market)
        assert passed


class TestAEGISFullChain:
    def test_all_gates_pass(self, proposal, portfolio, market):
        aegis = AEGIS()
        passed, results = aegis.check(proposal, portfolio, market)
        assert passed
        assert len(results) == 5

    def test_history_cleared_each_call(self, proposal, portfolio, market):
        aegis = AEGIS()
        aegis.check(proposal, portfolio, market)
        assert len(aegis.history) == 5
        aegis.check(proposal, portfolio, market)
        assert len(aegis.history) == 5
