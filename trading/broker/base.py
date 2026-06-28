from __future__ import annotations

"""Abstract broker interface.

All concrete brokers implement this ABC. Design principle:
- No per-query charges (subscription or free models only)
- Paper trading always available via HermesPaperBroker
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class OrderStatus(Enum):
    CREATED = auto()
    SUBMITTED = auto()
    PARTIALLY_FILLED = auto()
    FILLED = auto()
    CANCELLED = auto()
    REJECTED = auto()
    EXPIRED = auto()


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass
class Order:
    id: str = ""
    ticker: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    qty: float = 0.0
    price: float | None = None
    stop_price: float | None = None
    status: OrderStatus = OrderStatus.CREATED
    filled_qty: float = 0.0
    avg_fill_price: float | None = None
    created_at: str = ""
    filled_at: str | None = None
    reason: str = ""


@dataclass
class AccountInfo:
    cash: float = 0.0
    portfolio_value: float = 0.0
    buying_power: float = 0.0
    equity: float = 0.0
    day_pnl: float = 0.0


@dataclass
class Position:
    ticker: str
    qty: float
    market_value: float
    avg_entry_price: float
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0


class BaseBroker(ABC):
    name: str = "base"

    @abstractmethod
    def get_account(self) -> AccountInfo:
        ...

    @abstractmethod
    def get_positions(self) -> list[Position]:
        ...

    @abstractmethod
    def place_order(self, ticker: str, side: OrderSide, qty: float,
                    order_type: OrderType = OrderType.MARKET,
                    price: float | None = None,
                    stop_price: float | None = None) -> Order:
        ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        ...

    @abstractmethod
    def get_order(self, order_id: str) -> Order | None:
        ...

    @abstractmethod
    def get_orders(self, status: OrderStatus | None = None) -> list[Order]:
        ...
