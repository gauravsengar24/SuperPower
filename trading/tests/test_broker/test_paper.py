"""Tests for H.E.R.M.E.S. paper trading engine."""

import pytest
from trading.broker.paper import HermesPaperBroker
from trading.broker.base import OrderSide, OrderType, OrderStatus


@pytest.fixture
def broker():
    b = HermesPaperBroker(initial_cash=100_000.0, slippage=0.0,
                          fill_probability=1.0, latency_range=(0.0, 0.0))
    b.update_price("AAPL", 150.0)
    return b


class TestPaperBroker:
    def test_buy_fill(self, broker):
        order = broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
        assert order.status == OrderStatus.FILLED
        assert order.filled_qty == 10
        assert broker.cash < 100_000.0

    def test_sell_reduces_position(self, broker):
        broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
        broker.update_price("AAPL", 160.0)
        order = broker.place_order("AAPL", OrderSide.SELL, 5, OrderType.MARKET)
        assert order.status == OrderStatus.FILLED
        pos = broker.positions.get("AAPL", 0)
        assert pos == 5

    def test_insufficient_cash(self, broker):
        order = broker.place_order("AAPL", OrderSide.BUY, 10000, OrderType.MARKET)
        assert order.status in (OrderStatus.REJECTED, OrderStatus.PARTIALLY_FILLED)

    def test_cancel_order(self, broker):
        order = broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.LIMIT, price=100.0)
        assert broker.cancel_order(order.id)
        assert broker.get_order(order.id).status == OrderStatus.CANCELLED

    def test_get_account(self, broker):
        acct = broker.get_account()
        assert acct.cash == 100_000.0
        assert acct.portfolio_value == 100_000.0

    def test_get_positions_after_trade(self, broker):
        broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
        positions = broker.get_positions()
        assert len(positions) == 1
        assert positions[0].ticker == "AAPL"
        assert positions[0].qty == 10
