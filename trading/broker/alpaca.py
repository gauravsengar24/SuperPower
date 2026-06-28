from __future__ import annotations

"""Alpaca Markets broker adapter.

Free tier: paper trading + live trading with no per-query charges.
Requires ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables.
"""

import os
from datetime import datetime
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

_ALPACA_STATUS_MAP = {
    "new": OrderStatus.CREATED,
    "accepted": OrderStatus.SUBMITTED,
    "partially_filled": OrderStatus.PARTIALLY_FILLED,
    "filled": OrderStatus.FILLED,
    "canceled": OrderStatus.CANCELLED,
    "rejected": OrderStatus.REJECTED,
    "expired": OrderStatus.EXPIRED,
}


class AlpacaBroker(BaseBroker):
    name = "alpaca"

    def __init__(self, api_key: str | None = None,
                 secret_key: str | None = None,
                 base_url: str | None = None,
                 paper: bool = True):
        self.api_key = api_key or os.getenv("ALPACA_API_KEY", "")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY", "")
        self.base_url = (
            base_url
            or os.getenv("ALPACA_BASE_URL")
            or ("https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets")
        )
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from alpaca.trading.client import TradingClient
            self._client = TradingClient(
                api_key=self.api_key,
                secret_key=self.secret_key,
                paper="paper" in self.base_url,
            )
            return self._client
        except ImportError:
            raise ImportError(
                "alpaca-py is required for Alpaca broker. "
                "Install: pip install alpaca-py"
            )

    def _to_order_side(self, side: OrderSide) -> str:
        return side.value

    def _to_order_type(self, order_type: OrderType) -> str:
        return {
            OrderType.MARKET: "market",
            OrderType.LIMIT: "limit",
            OrderType.STOP: "stop",
            OrderType.STOP_LIMIT: "stop_limit",
        }[order_type]

    def get_account(self) -> AccountInfo:
        from alpaca.trading.enums import OrderStatus as AlpacaStatus
        client = self._get_client()
        acct = client.get_account()
        return AccountInfo(
            cash=float(acct.cash),
            portfolio_value=float(acct.portfolio_value),
            buying_power=float(acct.buying_power),
            equity=float(acct.equity),
        )

    def get_positions(self) -> list[Position]:
        client = self._get_client()
        positions = client.get_all_positions()
        return [
            Position(
                ticker=p.symbol,
                qty=float(p.qty),
                market_value=float(p.market_value),
                avg_entry_price=float(p.avg_entry_price),
                unrealized_pnl=float(p.unrealized_pl),
                unrealized_pnl_pct=float(p.unrealized_plpc),
            )
            for p in positions
        ]

    def place_order(self, ticker: str, side: OrderSide, qty: float,
                    order_type: OrderType = OrderType.MARKET,
                    price: float | None = None,
                    stop_price: float | None = None) -> Order:
        from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest, StopLimitOrderRequest
        client = self._get_client()
        try:
            if order_type == OrderType.MARKET:
                req = MarketOrderRequest(
                    symbol=ticker,
                    qty=qty,
                    side=self._to_order_side(side),
                    type="market",
                )
            elif order_type == OrderType.LIMIT:
                req = LimitOrderRequest(
                    symbol=ticker,
                    qty=qty,
                    side=self._to_order_side(side),
                    type="limit",
                    limit_price=price,
                )
            elif order_type == OrderType.STOP:
                req = StopOrderRequest(
                    symbol=ticker,
                    qty=qty,
                    side=self._to_order_side(side),
                    type="stop",
                    stop_price=stop_price,
                )
            else:
                req = StopLimitOrderRequest(
                    symbol=ticker,
                    qty=qty,
                    side=self._to_order_side(side),
                    type="stop_limit",
                    limit_price=price,
                    stop_price=stop_price,
                )
            alpaca_order = client.submit_order(order_data=req)
            return Order(
                id=alpaca_order.id,
                ticker=alpaca_order.symbol,
                side=side,
                order_type=order_type,
                qty=float(alpaca_order.qty),
                price=float(alpaca_order.limit_price) if alpaca_order.limit_price else None,
                stop_price=float(alpaca_order.stop_price) if alpaca_order.stop_price else None,
                status=_ALPACA_STATUS_MAP.get(alpaca_order.status, OrderStatus.SUBMITTED),
                created_at=str(alpaca_order.created_at),
            )
        except Exception as e:
            return Order(
                id="",
                ticker=ticker,
                side=side,
                order_type=order_type,
                qty=qty,
                status=OrderStatus.REJECTED,
                reason=str(e),
            )

    def cancel_order(self, order_id: str) -> bool:
        client = self._get_client()
        try:
            client.cancel_order_by_id(order_id)
            return True
        except Exception:
            return False

    def get_order(self, order_id: str) -> Order | None:
        client = self._get_client()
        try:
            o = client.get_order_by_id(order_id)
            return Order(
                id=o.id,
                ticker=o.symbol,
                qty=float(o.qty),
                status=_ALPACA_STATUS_MAP.get(o.status, OrderStatus.SUBMITTED),
                created_at=str(o.created_at),
            )
        except Exception:
            return None

    def get_orders(self, status: OrderStatus | None = None) -> list[Order]:
        client = self._get_client()
        try:
            orders = client.get_orders()
            return [
                Order(
                    id=o.id,
                    ticker=o.symbol,
                    qty=float(o.qty),
                    status=_ALPACA_STATUS_MAP.get(o.status, OrderStatus.SUBMITTED),
                    created_at=str(o.created_at),
                )
                for o in orders
            ]
        except Exception:
            return []
