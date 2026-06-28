"""M.I.D.A.S. — Market Iterative Decision & Analysis System.

Backtesting engine that walks a strategy across a date window,
executing through VELOCITY + AEGIS + ARCANE, and produces
performance metrics and reports.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from trading.broker.base import Order, OrderSide, OrderType, OrderStatus
from trading.broker.paper import HermesPaperBroker
from trading.portfolio.arcane import PortfolioState
from trading.backtesting.metrics import compute_metrics, compute_trade_metrics
from trading.risk.aegis import AEGIS, TradeProposal, PortfolioState as AEGISPortfolio, MarketSnapshot

logger = logging.getLogger(__name__)

SignalFunc = Callable[[str, str], str]


class BacktestStep:
    def __init__(self, date: str, signal: str, portfolio_value: float,
                 cash: float, positions_value: float, trade: Optional[dict] = None):
        self.date = date
        self.signal = signal
        self.portfolio_value = portfolio_value
        self.cash = cash
        self.positions_value = positions_value
        self.trade = trade or {}

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "signal": self.signal,
            "portfolio_value": self.portfolio_value,
            "cash": self.cash,
            "positions_value": self.positions_value,
            "trade": self.trade,
        }


class BacktestResult:
    def __init__(self, ticker: str, start_date: str, end_date: str,
                 steps: list[BacktestStep], initial_cash: float):
        self.ticker = ticker
        self.start_date = start_date
        self.end_date = end_date
        self.steps = steps
        self.initial_cash = initial_cash
        self._metrics = None
        self._trade_metrics = None

    @property
    def equity_curve(self) -> list[float]:
        return [self.initial_cash] + [s.portfolio_value for s in self.steps]

    @property
    def trades(self) -> list[dict]:
        return [s.trade for s in self.steps if s.trade.get("action") in ("buy", "sell")]

    @property
    def metrics(self) -> dict:
        if self._metrics is None:
            self._metrics = compute_metrics(self.equity_curve)
        return self._metrics

    @property
    def trade_metrics(self) -> dict:
        if self._trade_metrics is None:
            self._trade_metrics = compute_trade_metrics(self.trades)
        return self._trade_metrics

    def summary(self) -> str:
        m = self.metrics
        tm = self.trade_metrics
        lines = [
            f"M.I.D.A.S. Backtest: {self.ticker}",
            f"Period: {self.start_date} \u2192 {self.end_date}",
            f"Steps: {len(self.steps)}",
            "",
            "PERFORMANCE",
            f"  Total Return: {m['total_return_pct']}%",
            f"  CAGR: {m['cagr_pct']}%",
            f"  Sharpe: {m['sharpe_ratio']}",
            f"  Sortino: {m['sortino_ratio']}",
            f"  Max Drawdown: {m['max_drawdown_pct']}%",
            f"  Volatility: {m['volatility_pct']}%",
            "",
            "TRADES",
            f"  Total Trades: {tm['num_trades']}",
            f"  Win Rate: {tm['win_rate']}%",
            f"  Profit Factor: {tm['profit_factor']}",
            f"  Total P&L: ${tm['total_pnl']:,.2f}",
            f"  Avg Win: ${tm['avg_win']:,.2f}",
            f"  Avg Loss: ${tm['avg_loss']:,.2f}",
            "",
            f"Final Portfolio: ${m['final_value']:,.2f} (initial: ${m['initial_value']:,.2f})",
        ]
        return "\n".join(lines)


class MIDAS:
    def __init__(self, initial_cash: float = 100_000.0, aegis_config: Optional[dict] = None,
                 broker: Optional[HermesPaperBroker] = None):
        self.initial_cash = initial_cash
        self.aegis_config = aegis_config or {}
        self.broker = broker or HermesPaperBroker()
        self.portfolio = PortfolioState(initial_cash=initial_cash)

    def run(self, ticker: str, start_date: str, end_date: str,
            interval_days: int = 30, signal_func: Optional[SignalFunc] = None) -> BacktestResult:
        """Run a backtest using a signal function."""
        if signal_func is None:
            signal_func = self._default_signal

        dates = self._generate_dates(start_date, end_date, interval_days)
        steps: list[BacktestStep] = []

        for analysis_date in dates:
            signal = signal_func(ticker, analysis_date)
            self._update_prices(ticker, analysis_date)
            trade = self._execute_signal(ticker, signal, analysis_date)

            step = BacktestStep(
                date=analysis_date,
                signal=signal,
                portfolio_value=self.portfolio.total_value,
                cash=self.portfolio.cash,
                positions_value=self.portfolio.positions_value,
                trade=trade,
            )
            steps.append(step)

        return BacktestResult(
            ticker=ticker, start_date=start_date, end_date=end_date,
            steps=steps, initial_cash=self.initial_cash,
        )

    def _generate_dates(self, start: str, end: str, interval_days: int) -> list[str]:
        dates = []
        try:
            current = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            while current <= end_date:
                dates.append(current.strftime("%Y-%m-%d"))
                current += timedelta(days=interval_days)
        except ValueError as e:
            logger.error("Invalid date format: %s", e)
        return dates

    def _update_prices(self, ticker: str, date: str):
        try:
            import yfinance as yf
            df = yf.download(ticker, start=date, end=date, progress=False)
            if not df.empty:
                close = float(df["Close"].iloc[-1])
                self.broker.update_price(ticker, close)
                self.portfolio.update_prices({ticker: close})
        except Exception as e:
            logger.warning("Price fetch error for %s on %s: %s", ticker, date, e)

    def _execute_signal(self, ticker: str, signal: str, date: str) -> dict:
        action = self._signal_to_action(signal)
        if action == "hold":
            return {"action": "hold", "reason": "No trade signal"}

        price = self.broker._prices.get(ticker, 0.0)
        if price <= 0:
            return {"action": "skip", "reason": "No price data"}

        if action == "buy":
            risk_pct = self.aegis_config.get("default_risk_per_trade", 0.02)
            max_risk = self.portfolio.cash * risk_pct
            if max_risk <= 0:
                return {"action": "skip", "reason": "Insufficient cash"}
            qty = max(1, int(max_risk / price))
        elif action == "sell":
            pos = self.portfolio.positions.get(ticker.upper())
            if not pos or pos.qty <= 0:
                return {"action": "skip", "reason": "No position to sell"}
            qty = int(pos.qty)
        else:
            return {"action": "hold", "reason": f"Unknown signal: {signal}"}

        if not self._aegis_check(ticker, action, qty, price):
            return {"action": "blocked", "reason": "AEGIS risk gate rejected"}

        side = OrderSide.BUY if action == "buy" else OrderSide.SELL
        order = self.broker.place_order(
            ticker=ticker, side=side, qty=qty,
            order_type=OrderType.MARKET,
        )

        if order.status == OrderStatus.FILLED:
            self.portfolio.apply_fill(order)
            return {
                "action": action,
                "qty": order.filled_qty,
                "price": order.avg_fill_price or price,
            }
        return {"action": "failed", "reason": f"Order {order.status.name}: {order.reason}"}

    def _aegis_check(self, ticker: str, action: str, qty: int, price: float) -> bool:
        ps = AEGISPortfolio(
            positions=[], cash=self.portfolio.cash,
            total_value=self.portfolio.total_value,
            peak_value=self.portfolio.peak_value,
            daily_start_value=self.portfolio.daily_start_value,
            initial_value=self.initial_cash,
        )
        ms = MarketSnapshot(ticker=ticker, price=price, vix=15.0)
        proposal = TradeProposal(
            ticker=ticker, side=action, qty=float(qty),
            order_type="market", estimated_value=qty * price,
            confidence=0.5,
        )
        aegis = AEGIS(self.aegis_config)
        all_pass, _ = aegis.check(proposal, ps, ms)
        return all_pass

    def _signal_to_action(self, signal: str) -> str:
        s = signal.upper().strip()
        if s in ("STRONG_BUY", "BUY"):
            return "buy"
        if s in ("STRONG_SELL", "SELL"):
            return "sell"
        return "hold"

    def _default_signal(self, ticker: str, date: str) -> str:
        try:
            import yfinance as yf
            df = yf.download(ticker, period="1y", progress=False)
            if df.empty:
                return "HOLD"
            close = float(df["Close"].iloc[-1])
            sma200 = float(df["Close"].rolling(200).mean().iloc[-1])
            if sma200 != sma200 or sma200 == 0:
                return "HOLD"
            if close < sma200 * 0.95:
                return "STRONG_BUY"
            if close < sma200:
                return "BUY"
            if close > sma200 * 1.05:
                return "STRONG_SELL"
            if close > sma200:
                return "SELL"
            return "HOLD"
        except Exception:
            return "HOLD"
