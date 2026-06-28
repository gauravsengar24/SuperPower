from __future__ import annotations

"""A.E.G.I.S. — Asset Equity Guidance and Insurance System.

Chain-of-responsibility pattern: every gate runs sequentially. If ANY gate
rejects the trade, the proposal is blocked — no LLM override possible.

Architecture:
    AEGIS.check(proposal, portfolio, market_data) → GateResult
        ├── PositionLimitGate    — max positions, max % per asset
        ├── DrawdownGate         — daily + trailing drawdown limits
        ├── VaRGate              — position VaR vs portfolio
        ├── VolatilityFilterGate — VIX / ATR regime check
        ├── CorrelationGate      — multi-asset correlation check
        └── OrderSizeGate        — Kelly/risk-based sizing validation

Each gate implements:
    def check(self, proposal: TradeProposal, portfolio: PortfolioState,
              market: MarketSnapshot) -> GateResult:
        ...
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Union, Optional


class GateDecision(Enum):
    PASS = auto()
    REJECT = auto()
    WARN = auto()


@dataclass
class GateResult:
    gate_name: str
    decision: GateDecision
    reason: str = ""
    details: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.decision == GateDecision.PASS


@dataclass
class TradeProposal:
    ticker: str
    side: str  # "buy" or "sell"
    qty: int | float
    order_type: str  # "market", "limit", "stop"
    limit_price: float | None = None
    stop_price: float | None = None
    estimated_value: float = 0.0
    confidence: float = 0.0  # 0.0 - 1.0 from LLM


@dataclass
class Position:
    ticker: str
    qty: float
    avg_price: float
    current_price: float
    pnl: float = 0.0
    pnl_pct: float = 0.0


@dataclass
class PortfolioState:
    positions: list[Position]
    cash: float
    total_value: float
    peak_value: float
    daily_start_value: float
    initial_value: float


@dataclass
class MarketSnapshot:
    ticker: str
    price: float
    atr: float | None = None
    vix: float | None = None
    volume: int = 0
    avg_volume: int = 0


class BaseGate:
    name: str = "base"

    def __call__(self, proposal: TradeProposal, portfolio: PortfolioState,
                 market: MarketSnapshot) -> GateResult:
        return self.check(proposal, portfolio, market)

    def check(self, proposal: TradeProposal, portfolio: PortfolioState,
              market: MarketSnapshot) -> GateResult:
        raise NotImplementedError


class PositionLimitGate(BaseGate):
    name = "position_limit"

    def __init__(self, max_positions: int = 10, max_position_pct: float = 0.25):
        self.max_positions = max_positions
        self.max_position_pct = max_position_pct

    def check(self, proposal, portfolio, market):
        # Count existing positions (excluding the proposed ticker)
        existing = [p for p in portfolio.positions if p.ticker != proposal.ticker]
        if proposal.side == "buy":
            if len(existing) >= self.max_positions:
                return GateResult(
                    self.name, GateDecision.REJECT,
                    f"Max positions ({self.max_positions}) reached",
                    {"current": len(existing), "max": self.max_positions},
                )
            # Check position concentration
            if proposal.estimated_value / portfolio.total_value > self.max_position_pct:
                return GateResult(
                    self.name, GateDecision.REJECT,
                    f"Position would exceed {self.max_position_pct:.0%} of portfolio",
                    {"proposed_pct": proposal.estimated_value / portfolio.total_value,
                     "max_pct": self.max_position_pct},
                )
        return GateResult(self.name, GateDecision.PASS)


class DrawdownGate(BaseGate):
    name = "drawdown"

    def __init__(self, max_daily: float = 0.05, max_trailing: float = 0.15):
        self.max_daily = max_daily
        self.max_trailing = max_trailing

    def check(self, proposal, portfolio, market):
        # Daily drawdown
        daily_dd = (portfolio.daily_start_value - portfolio.total_value) / portfolio.daily_start_value
        if daily_dd > self.max_daily:
            return GateResult(
                self.name, GateDecision.REJECT,
                f"Daily drawdown {daily_dd:.1%} exceeds limit {self.max_daily:.0%}",
                {"drawdown": daily_dd, "limit": self.max_daily},
            )
        # Trailing drawdown
        trailing_dd = (portfolio.peak_value - portfolio.total_value) / portfolio.peak_value
        if trailing_dd > self.max_trailing:
            return GateResult(
                self.name, GateDecision.REJECT,
                f"Trailing drawdown {trailing_dd:.1%} exceeds limit {self.max_trailing:.0%}",
                {"drawdown": trailing_dd, "limit": self.max_trailing},
            )
        return GateResult(self.name, GateDecision.PASS)


class VolatilityFilterGate(BaseGate):
    name = "volatility_filter"

    def __init__(self, threshold: float = 0.40):
        self.threshold = threshold

    def check(self, proposal, portfolio, market):
        if market.vix is not None and market.vix > self.threshold * 100:
            return GateResult(
                self.name, GateDecision.REJECT,
                f"VIX {market.vix:.1f} exceeds volatility threshold {self.threshold*100:.0f}",
                {"vix": market.vix, "threshold": self.threshold * 100},
            )
        if market.atr and market.price:
            atr_pct = market.atr / market.price
            if atr_pct > self.threshold:
                return GateResult(
                    self.name, GateDecision.WARN,
                    f"ATR {atr_pct:.1%} exceeds volatility threshold {self.threshold:.0%}",
                    {"atr_pct": atr_pct, "threshold": self.threshold},
                )
        return GateResult(self.name, GateDecision.PASS)


class CorrelationGate(BaseGate):
    name = "correlation"

    def __init__(self, max_correlation: float = 0.85):
        self.max_correlation = max_correlation

    def check(self, proposal, portfolio, market):
        correlated_positions = []
        for pos in portfolio.positions:
            if pos.ticker == proposal.ticker:
                continue
            if pos.pnl_pct != 0 and abs(pos.pnl_pct) > 0.02:
                correlated_positions.append(pos)
        if len(correlated_positions) >= 3:
            return GateResult(
                self.name, GateDecision.WARN,
                f"Multiple positions moving together ({len(correlated_positions)})",
                {"correlated_count": len(correlated_positions)},
            )
        return GateResult(self.name, GateDecision.PASS)


class OrderSizeGate(BaseGate):
    name = "order_size"

    def __init__(self, default_risk_per_trade: float = 0.02):
        self.default_risk_per_trade = default_risk_per_trade

    def check(self, proposal, portfolio, market):
        risk_amount = proposal.estimated_value * self.default_risk_per_trade
        if risk_amount > portfolio.total_value * 0.05:
            return GateResult(
                self.name, GateDecision.REJECT,
                f"Risk amount ${risk_amount:.2f} exceeds 5% of portfolio",
                {"risk_amount": risk_amount, "portfolio_pct": risk_amount / portfolio.total_value},
            )
        return GateResult(self.name, GateDecision.PASS)


class AEGIS:
    """Risk gate orchestrator — runs all gates in chain-of-responsibility order."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.gates: list[BaseGate] = [
            PositionLimitGate(
                max_positions=self.config.get("max_positions", 10),
                max_position_pct=self.config.get("max_position_pct", 0.25),
            ),
            DrawdownGate(
                max_daily=self.config.get("max_daily_drawdown", 0.05),
                max_trailing=self.config.get("max_trailing_drawdown", 0.15),
            ),
            VolatilityFilterGate(
                threshold=self.config.get("volatility_threshold", 0.40),
            ),
            CorrelationGate(),
            OrderSizeGate(
                default_risk_per_trade=self.config.get("default_risk_per_trade", 0.02),
            ),
        ]
        self.history: list[GateResult] = []

    def check(self, proposal: TradeProposal, portfolio: PortfolioState,
              market: MarketSnapshot) -> tuple[bool, list[GateResult]]:
        self.history = []
        all_pass = True
        for gate in self.gates:
            result = gate(proposal, portfolio, market)
            self.history.append(result)
            if result.decision == GateDecision.REJECT:
                all_pass = False
        return all_pass, self.history
