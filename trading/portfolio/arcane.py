from __future__ import annotations

"""A.R.C.A.N.E. — Algorithmic Risk, Capital, and Analytic Network Engine.

Manages portfolio state: positions, P&L, allocation targets, rebalancing.
Integrates with AEGIS for risk-gated execution and VELOCITY for order routing.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trading.broker.base import Order, OrderSide, OrderStatus, Position as BrokerPosition


class PortfolioPosition:
    def __init__(self, ticker: str, qty: float = 0.0,
                 avg_price: float = 0.0, current_price: float = 0.0):
        self.ticker = ticker.upper()
        self.qty = qty
        self.avg_price = avg_price
        self.current_price = current_price

    @property
    def market_value(self) -> float:
        return self.qty * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.qty * self.avg_price

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_pct(self) -> float:
        return self.unrealized_pnl / self.cost_basis if self.cost_basis else 0.0

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "qty": self.qty,
            "avg_price": self.avg_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "cost_basis": self.cost_basis,
            "unrealized_pnl": self.unrealized_pnl,
            "unrealized_pnl_pct": self.unrealized_pnl_pct,
        }


class PortfolioState:
    def __init__(self, initial_cash: float = 100_000.0):
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.positions: dict[str, PortfolioPosition] = {}
        self.trade_history: list[dict] = []
        self.peak_value = initial_cash
        self.daily_start_value = initial_cash

    @property
    def positions_value(self) -> float:
        return sum(p.market_value for p in self.positions.values())

    @property
    def total_value(self) -> float:
        return self.cash + self.positions_value

    @property
    def daily_drawdown(self) -> float:
        return (self.daily_start_value - self.total_value) / self.daily_start_value if self.daily_start_value else 0.0

    @property
    def trailing_drawdown(self) -> float:
        return (self.peak_value - self.total_value) / self.peak_value if self.peak_value else 0.0

    @property
    def positions_list(self) -> list[PortfolioPosition]:
        return list(self.positions.values())

    def update_prices(self, prices: dict[str, float]):
        for ticker, price in prices.items():
            if ticker.upper() in self.positions:
                self.positions[ticker.upper()].current_price = price
        if self.total_value > self.peak_value:
            self.peak_value = self.total_value

    def apply_fill(self, order: Order):
        ticker = order.ticker.upper()
        qty = order.filled_qty
        price = order.avg_fill_price or 0.0
        if order.side == OrderSide.BUY:
            if ticker not in self.positions:
                self.positions[ticker] = PortfolioPosition(ticker)
            pos = self.positions[ticker]
            new_total_qty = pos.qty + qty
            pos.avg_price = round(((pos.avg_price * pos.qty) + (price * qty)) / new_total_qty, 2) if new_total_qty > 0 else price
            pos.qty = new_total_qty
            pos.current_price = price
            self.cash -= price * qty
        else:
            if ticker in self.positions:
                pos = self.positions[ticker]
                pos.qty = max(0.0, pos.qty - qty)
                pos.current_price = price
                self.cash += price * qty
                if pos.qty == 0:
                    del self.positions[ticker]
        self.trade_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ticker": ticker,
            "side": order.side.value,
            "qty": qty,
            "price": price,
            "order_type": order.order_type.value,
            "order_id": order.id,
        })
        if self.total_value > self.peak_value:
            self.peak_value = self.total_value

    def to_dict(self) -> dict:
        return {
            "cash": self.cash,
            "initial_cash": self.initial_cash,
            "total_value": self.total_value,
            "positions_value": self.positions_value,
            "positions": {t: p.to_dict() for t, p in self.positions.items()},
            "peak_value": self.peak_value,
            "daily_start_value": self.daily_start_value,
            "total_return_pct": (self.total_value - self.initial_cash) / self.initial_cash if self.initial_cash else 0.0,
        }


class ARCANE:
    def __init__(self, config: dict | None = None, state_path: str | None = None):
        self.config = config or {}
        self.state_path = Path(state_path or "~/.trading/portfolio/state.json").expanduser()
        self.portfolio = PortfolioState(
            initial_cash=self.config.get("initial_cash", 100_000.0)
        )
        self._load_state()

    def _load_state(self):
        if self.state_path.exists():
            try:
                data = json.loads(self.state_path.read_text())
                self.portfolio.cash = data.get("cash", self.portfolio.initial_cash)
                self.portfolio.peak_value = data.get("peak_value", self.portfolio.initial_cash)
                self.portfolio.daily_start_value = data.get("daily_start_value", self.portfolio.initial_cash)
                for ticker, pdata in data.get("positions", {}).items():
                    pos = PortfolioPosition(
                        ticker=ticker,
                        qty=pdata.get("qty", 0),
                        avg_price=pdata.get("avg_price", 0),
                        current_price=pdata.get("current_price", 0),
                    )
                    self.portfolio.positions[ticker] = pos
                for t in data.get("trade_history", []):
                    self.portfolio.trade_history.append(t)
            except (json.JSONDecodeError, KeyError):
                pass

    def _save_state(self):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.portfolio.to_dict(), indent=2))

    def record_order(self, order: Order):
        if order.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
            self.portfolio.apply_fill(order)
            self._save_state()

    def get_performance_metrics(self) -> dict:
        p = self.portfolio
        returns = (p.total_value - p.initial_cash) / p.initial_cash if p.initial_cash else 0.0
        return {
            "total_return": round(returns, 4),
            "total_return_pct": round(returns * 100, 2),
            "cash": round(p.cash, 2),
            "total_value": round(p.total_value, 2),
            "positions_value": round(p.positions_value, 2),
            "num_positions": len(p.positions),
            "peak_value": round(p.peak_value, 2),
            "daily_drawdown": round(p.daily_drawdown, 4),
            "trailing_drawdown": round(p.trailing_drawdown, 4),
            "trade_count": len(p.trade_history),
        }
