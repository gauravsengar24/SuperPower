"""Tests for V.E.L.O.C.I.T.Y. execution engine."""

import pytest
from trading.execution.velocity import VELOCITY, ExecutionReport
from trading.broker.paper import HermesPaperBroker
from trading.risk.aegis import AEGIS, PortfolioState, Position, MarketSnapshot, TradeProposal


@pytest.fixture
def broker():
    b = HermesPaperBroker(initial_cash=100_000.0, slippage=0.0,
                          fill_probability=1.0, latency_range=(0.0, 0.0))
    b.update_price("AAPL", 150.0)
    return b


class TestVELOCITY:
    def test_successful_market_order(self, broker):
        velo = VELOCITY(broker=broker, paper_mode=True)
        report = velo.execute("AAPL", "buy", 10, "market")
        assert report.success
        assert report.order is not None
        assert report.order.status.name == "FILLED"

    def test_aegis_blocks_trade(self, broker):
        portfolio = PortfolioState(
            positions=[Position(f"T{i}", 100, 100, 100) for i in range(10)],
            cash=0, total_value=1000, peak_value=1000,
            daily_start_value=1000, initial_value=1000,
        )
        market = MarketSnapshot(ticker="AAPL", price=150.0, vix=15.0)
        aegis = AEGIS({"max_positions": 5})
        velo = VELOCITY(broker=broker, aegis=aegis)
        report = velo.execute("AAPL", "buy", 10, "market",
                              portfolio_state=portfolio,
                              market_snapshot=market)
        assert not report.success
        assert "AEGIS" in report.message
