"""Performance metrics for backtesting."""

import math
from typing import Sequence


def compute_metrics(equity_curve: Sequence[float], risk_free_rate: float = 0.05) -> dict:
    """Compute standard backtest metrics from an equity curve.
    
    Args:
        equity_curve: List of portfolio values at each step (including initial).
        risk_free_rate: Annual risk-free rate (default 5%).
    """
    if len(equity_curve) < 2:
        return {
            "total_return_pct": 0.0,
            "cagr_pct": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown_pct": 0.0,
            "volatility_pct": 0.0,
            "win_rate": 0.0,
            "num_trades": 0,
        }

    returns = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1]
        if prev != 0:
            returns.append((equity_curve[i] - prev) / prev)
        else:
            returns.append(0.0)

    total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0]

    n = len(returns)
    avg_return = sum(returns) / n if n > 0 else 0.0
    variance = sum((r - avg_return) ** 2 for r in returns) / n if n > 0 else 0.0
    std_dev = math.sqrt(variance) if variance > 0 else 0.0

    downside_returns = [r for r in returns if r < 0]
    downside_variance = sum(r ** 2 for r in downside_returns) / n if n > 0 else 0.0
    downside_std = math.sqrt(downside_variance) if downside_variance > 0 else 0.0

    periods_per_year = _estimate_periods_per_year(equity_curve)

    if std_dev > 0:
        excess_return = avg_return - (risk_free_rate / periods_per_year)
        sharpe = (excess_return / std_dev) * math.sqrt(periods_per_year) if std_dev > 0 else 0.0
    else:
        sharpe = 0.0

    if downside_std > 0:
        sortino = (avg_return - (risk_free_rate / periods_per_year)) / downside_std * math.sqrt(periods_per_year) if downside_std > 0 else 0.0
    else:
        sortino = 0.0

    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    n_years = len(equity_curve) / periods_per_year if periods_per_year > 0 else 1.0
    cagr = (equity_curve[-1] / equity_curve[0]) ** (1.0 / n_years) - 1 if equity_curve[0] > 0 and n_years > 0 else 0.0

    return {
        "total_return_pct": round(total_return * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "volatility_pct": round(std_dev * math.sqrt(periods_per_year) * 100, 2),
        "num_periods": n,
        "final_value": round(equity_curve[-1], 2),
        "initial_value": round(equity_curve[0], 2),
    }


def compute_trade_metrics(trades: list[dict]) -> dict:
    """Compute trade-level metrics from a list of trade records."""
    if not trades:
        return {"win_rate": 0.0, "num_trades": 0, "avg_win": 0.0, "avg_loss": 0.0, "profit_factor": 0.0}

    wins = [t for t in trades if t.get("pnl", 0) > 0]
    losses = [t for t in trades if t.get("pnl", 0) < 0]

    total_wins = sum(t["pnl"] for t in wins) if wins else 0.0
    total_losses = abs(sum(t["pnl"] for t in losses)) if losses else 0.0

    return {
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0.0,
        "num_trades": len(trades),
        "avg_win": round(total_wins / len(wins), 2) if wins else 0.0,
        "avg_loss": round(-total_losses / len(losses), 2) if losses else 0.0,
        "profit_factor": round(total_wins / total_losses, 2) if total_losses > 0 else float("inf") if total_wins > 0 else 0.0,
        "total_pnl": round(sum(t.get("pnl", 0) for t in trades), 2),
    }


def _estimate_periods_per_year(equity_curve: Sequence[float]) -> float:
    """Estimate number of periods per year from equity curve length."""
    n = len(equity_curve)
    if n <= 1:
        return 252
    if n <= 30:
        return 12
    if n <= 60:
        return 52
    return 252
