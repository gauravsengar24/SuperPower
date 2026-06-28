"""Tests for backtesting metrics module."""

from trading.backtesting.metrics import compute_metrics, compute_trade_metrics


def test_flat_curve():
    curve = [100000.0, 100000.0, 100000.0]
    m = compute_metrics(curve)
    assert m["total_return_pct"] == 0.0
    assert m["max_drawdown_pct"] == 0.0


def test_upward_curve():
    curve = [100000.0, 105000.0, 110000.0, 115000.0]
    m = compute_metrics(curve)
    assert m["total_return_pct"] == 15.0
    assert m["max_drawdown_pct"] == 0.0


def test_downward_curve():
    curve = [100000.0, 95000.0, 90000.0]
    m = compute_metrics(curve)
    assert m["total_return_pct"] == -10.0
    assert m["max_drawdown_pct"] == 10.0


def test_volatile_curve():
    curve = [100000.0, 110000.0, 95000.0, 105000.0]
    m = compute_metrics(curve)
    assert m["total_return_pct"] == 5.0
    assert m["max_drawdown_pct"] > 0.0


def test_single_value():
    m = compute_metrics([100000.0])
    assert m["sharpe_ratio"] == 0.0
    assert m["total_return_pct"] == 0.0


def test_trade_metrics_empty():
    tm = compute_trade_metrics([])
    assert tm["num_trades"] == 0
    assert tm["win_rate"] == 0.0


def test_trade_metrics_all_wins():
    trades = [
        {"pnl": 500, "action": "sell"},
        {"pnl": 300, "action": "sell"},
    ]
    tm = compute_trade_metrics(trades)
    assert tm["num_trades"] == 2
    assert tm["win_rate"] == 100.0
    assert tm["total_pnl"] == 800.0


def test_trade_metrics_mixed():
    trades = [
        {"pnl": 1000, "action": "sell"},
        {"pnl": -200, "action": "sell"},
        {"pnl": 500, "action": "sell"},
    ]
    tm = compute_trade_metrics(trades)
    assert tm["num_trades"] == 3
    assert tm["win_rate"] == 66.7
    assert tm["total_pnl"] == 1300.0


def test_profit_factor():
    trades = [
        {"pnl": 1000, "action": "sell"},
        {"pnl": -500, "action": "sell"},
    ]
    tm = compute_trade_metrics(trades)
    assert tm["profit_factor"] == 2.0
