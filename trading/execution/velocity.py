from __future__ import annotations

"""V.E.L.O.C.I.T.Y. — Execution Engine.

Pipeline: Validate order → Route to broker → Monitor fill → Report back.
Integrates with AEGIS (pre-execution risk check) and ARCANE (post-fill portfolio update).
"""

import logging
from typing import Any

from trading.broker.base import (
    BaseBroker,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
)
from trading.risk.aegis import AEGIS, MarketSnapshot, PortfolioState, TradeProposal

logger = logging.getLogger(__name__)


class ExecutionReport:
    def __init__(self, success: bool, order: Order | None = None,
                 message: str = "", risk_results: list | None = None):
        self.success = success
        self.order = order
        self.message = message
        self.risk_results = risk_results or []


class VELOCITY:
    def __init__(self, broker: BaseBroker, aegis: AEGIS | None = None,
                 paper_mode: bool = True):
        self.broker = broker
        self.aegis = aegis
        self.paper_mode = paper_mode

    def execute(self, ticker: str, side: str, qty: float,
                order_type: str = "market",
                price: float | None = None,
                stop_price: float | None = None,
                portfolio_state: PortfolioState | None = None,
                market_snapshot: MarketSnapshot | None = None) -> ExecutionReport:

        proposal = TradeProposal(
            ticker=ticker.upper(),
            side=side,
            qty=qty,
            order_type=order_type,
            limit_price=price,
            stop_price=stop_price,
        )

        # AEGIS risk check
        if self.aegis and portfolio_state and market_snapshot:
            all_pass, results = self.aegis.check(proposal, portfolio_state, market_snapshot)
            if not all_pass:
                rejected = [r for r in results if not r.passed]
                reasons = "; ".join(f"{r.gate_name}: {r.reason}" for r in rejected)
                logger.warning("AEGIS blocked trade %s %s %s: %s", side, qty, ticker, reasons)
                return ExecutionReport(
                    success=False,
                    message=f"AEGIS rejected: {reasons}",
                    risk_results=results,
                )

        # Map order type string to enum
        type_map = {
            "market": OrderType.MARKET,
            "limit": OrderType.LIMIT,
            "stop": OrderType.STOP,
            "stop_limit": OrderType.STOP_LIMIT,
        }
        ot = type_map.get(order_type.lower(), OrderType.MARKET)
        side_enum = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

        try:
            order = self.broker.place_order(
                ticker=ticker.upper(),
                side=side_enum,
                qty=qty,
                order_type=ot,
                price=price,
                stop_price=stop_price,
            )
            if order.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
                logger.info("Order filled: %s %s %s @ %.2f",
                            order.side.value, order.filled_qty, order.ticker,
                            order.avg_fill_price or 0)
                return ExecutionReport(
                    success=True,
                    order=order,
                    message=f"Order {order.id} filled {order.filled_qty} @ {order.avg_fill_price}",
                )
            else:
                logger.warning("Order not filled: status=%s reason=%s",
                               order.status, order.reason)
                return ExecutionReport(
                    success=False,
                    order=order,
                    message=f"Order {order.id}: {order.status.name} - {order.reason}",
                )
        except Exception as e:
            logger.error("Execution failed: %s", e)
            return ExecutionReport(success=False, message=str(e))
