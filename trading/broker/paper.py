"""H.E.R.M.E.S. — Paper Trading Engine.

Simulates order fills with configurable slippage, latency, and partial fills.
No real money involved — safe for strategy testing.
"""

import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from .base import (
    AccountInfo,
    BaseBroker,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
)


class HermesPaperBroker(BaseBroker):
    name = "paper"

    def __init__(self, initial_cash: float = 100_000.0,
                 slippage: float = 0.001,
                 fill_probability: float = 0.95,
                 latency_range: tuple[float, float] = (0.05, 0.3)):
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.positions: dict[str, float] = {}
        self.avg_prices: dict[str, float] = {}
        self.orders: dict[str, Order] = {}
        self.filled_orders: list[Order] = []
        self.slippage = slippage
        self.fill_probability = fill_probability
        self.latency_range = latency_range
        self._prices: dict[str, float] = {}

    def update_price(self, ticker: str, price: float):
        self._prices[ticker.upper()] = price

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def get_account(self) -> AccountInfo:
        pos_value = sum(
            qty * self._prices.get(t, 0.0)
            for t, qty in self.positions.items()
        )
        return AccountInfo(
            cash=self.cash,
            portfolio_value=self.cash + pos_value,
            buying_power=self.cash * 2,
            equity=self.cash + pos_value,
            day_pnl=pos_value - self.initial_cash,
        )

    def get_positions(self) -> list[Position]:
        result = []
        for ticker, qty in self.positions.items():
            price = self._prices.get(ticker, 0.0)
            avg = self.avg_prices.get(ticker, price)
            result.append(Position(
                ticker=ticker,
                qty=qty,
                market_value=qty * price,
                avg_entry_price=avg,
                unrealized_pnl=(price - avg) * qty,
                unrealized_pnl_pct=(price - avg) / avg if avg else 0,
            ))
        return result

    def place_order(self, ticker: str, side: OrderSide, qty: float,
                    order_type: OrderType = OrderType.MARKET,
                    price: float | None = None,
                    stop_price: float | None = None) -> Order:
        time.sleep(random.uniform(*self.latency_range))
        ticker = ticker.upper()
        order_id = str(uuid.uuid4())
        order = Order(
            id=order_id,
            ticker=ticker,
            side=side,
            order_type=order_type,
            qty=qty,
            price=price,
            stop_price=stop_price,
            status=OrderStatus.CREATED,
            created_at=self._now(),
        )

        if order_type == OrderType.MARKET:
            order = self._fill_market(order)
        elif order_type == OrderType.LIMIT:
            order = self._evaluate_limit(order)
        elif order_type == OrderType.STOP:
            order = self._evaluate_stop(order)

        self.orders[order_id] = order
        if order.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
            self.filled_orders.append(order)
        return order

    def _fill_market(self, order: Order) -> Order:
        if random.random() > self.fill_probability:
            order.status = OrderStatus.REJECTED
            order.reason = "Simulated rejection"
            return order
        base_price = self._prices.get(order.ticker, 100.0)
        slip = base_price * self.slippage * random.uniform(0.5, 1.5)
        fill_price = base_price + slip if order.side == OrderSide.BUY else base_price - slip
        total_cost = fill_price * order.qty
        if order.side == OrderSide.BUY and total_cost > self.cash:
            max_qty = int(self.cash / fill_price)
            if max_qty == 0:
                order.status = OrderStatus.REJECTED
                order.reason = "Insufficient cash"
                return order
            order.filled_qty = max_qty
            order.qty = max_qty
            order.status = OrderStatus.PARTIALLY_FILLED
        else:
            order.filled_qty = order.qty
            order.status = OrderStatus.FILLED
        order.avg_fill_price = round(fill_price, 2)
        order.filled_at = self._now()
        self._update_position(order)
        return order

    def _evaluate_limit(self, order: Order) -> Order:
        current = self._prices.get(order.ticker, 0.0)
        if order.side == OrderSide.BUY and order.price and current <= order.price:
            return self._fill_market(order)
        elif order.side == OrderSide.SELL and order.price and current >= order.price:
            return self._fill_market(order)
        order.status = OrderStatus.SUBMITTED
        return order

    def _evaluate_stop(self, order: Order) -> Order:
        current = self._prices.get(order.ticker, 0.0)
        if order.side == OrderSide.BUY and order.stop_price and current >= order.stop_price:
            return self._fill_market(order)
        elif order.side == OrderSide.SELL and order.stop_price and current <= order.stop_price:
            return self._fill_market(order)
        order.status = OrderStatus.SUBMITTED
        return order

    def _update_position(self, order: Order):
        ticker = order.ticker
        filled = order.filled_qty
        if order.side == OrderSide.BUY:
            avg = self.avg_prices.get(ticker, 0.0)
            old_qty = self.positions.get(ticker, 0.0)
            new_avg = ((avg * old_qty) + (order.avg_fill_price * filled)) / (old_qty + filled) if (old_qty + filled) > 0 else order.avg_fill_price
            self.avg_prices[ticker] = round(new_avg, 2)
            self.positions[ticker] = old_qty + filled
            self.cash -= order.avg_fill_price * filled
        else:
            old_qty = self.positions.get(ticker, 0.0)
            self.positions[ticker] = max(0, old_qty - filled)
            self.cash += order.avg_fill_price * filled
            if self.positions[ticker] == 0:
                self.avg_prices.pop(ticker, None)

    def cancel_order(self, order_id: str) -> bool:
        order = self.orders.get(order_id)
        if order and order.status in (OrderStatus.CREATED, OrderStatus.SUBMITTED):
            order.status = OrderStatus.CANCELLED
            return True
        return False

    def get_order(self, order_id: str) -> Order | None:
        return self.orders.get(order_id)

    def get_orders(self, status: OrderStatus | None = None) -> list[Order]:
        if status:
            return [o for o in self.orders.values() if o.status == status]
        return list(self.orders.values())
