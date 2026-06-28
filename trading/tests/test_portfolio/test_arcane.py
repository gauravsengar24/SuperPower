"""Tests for A.R.C.A.N.E. portfolio management."""

import pytest
from trading.portfolio.arcane import ARCANE, PortfolioPosition, PortfolioState
from trading.broker.base import Order, OrderSide, OrderType, OrderStatus


class TestPortfolioState:
    def test_empty_portfolio(self):
        p = PortfolioState(initial_cash=100_000.0)
        assert p.cash == 100_000.0
        assert p.total_value == 100_000.0
        assert p.positions_value == 0.0

    def test_update_prices(self):
        p = PortfolioState()
        p.positions["AAPL"] = PortfolioPosition("AAPL", qty=10, avg_price=150.0)
        p.update_prices({"AAPL": 160.0})
        assert p.positions["AAPL"].current_price == 160.0
        assert p.positions_value == 1600.0

    def test_apply_buy_fill(self):
        p = PortfolioState()
        order = Order(
            id="test1", ticker="AAPL", side=OrderSide.BUY,
            order_type=OrderType.MARKET, qty=10, filled_qty=10,
            avg_fill_price=150.0, status=OrderStatus.FILLED,
        )
        p.apply_fill(order)
        assert "AAPL" in p.positions
        assert p.positions["AAPL"].qty == 10
        assert p.cash < 100_000.0

    def test_apply_sell_fill(self):
        p = PortfolioState()
        p.positions["AAPL"] = PortfolioPosition("AAPL", qty=10, avg_price=150.0, current_price=160.0)
        old_cash = p.cash
        order = Order(
            id="test2", ticker="AAPL", side=OrderSide.SELL,
            order_type=OrderType.MARKET, qty=10, filled_qty=10,
            avg_fill_price=160.0, status=OrderStatus.FILLED,
        )
        p.apply_fill(order)
        assert "AAPL" not in p.positions
        assert p.cash > old_cash


class TestARCANE:
    def test_performance_metrics(self, tmp_path):
        state_file = tmp_path / "state.json"
        arcane = ARCANE(state_path=str(state_file))
        metrics = arcane.get_performance_metrics()
        assert metrics["total_return"] == 0.0
        assert metrics["num_positions"] == 0
        assert metrics["trade_count"] == 0

    def test_record_order_updates_portfolio(self, tmp_path):
        state_file = tmp_path / "state.json"
        arcane = ARCANE(state_path=str(state_file))
        order = Order(
            id="test", ticker="AAPL", side=OrderSide.BUY,
            order_type=OrderType.MARKET, qty=10, filled_qty=10,
            avg_fill_price=150.0, status=OrderStatus.FILLED,
        )
        arcane.record_order(order)
        metrics = arcane.get_performance_metrics()
        assert metrics["num_positions"] == 1
        assert metrics["trade_count"] == 1
