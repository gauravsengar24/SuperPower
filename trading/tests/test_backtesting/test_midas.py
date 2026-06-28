"""Tests for MIDAS backtesting engine."""

from trading.backtesting.midas import MIDAS, BacktestStep, BacktestResult


def test_midas_init():
    m = MIDAS(initial_cash=50000)
    assert m.initial_cash == 50000
    assert m.portfolio.cash == 50000


def test_backtest_step():
    step = BacktestStep("2026-01-15", "BUY", 100000.0, 50000.0, 50000.0,
                        {"action": "buy", "qty": 10, "price": 150.0})
    d = step.to_dict()
    assert d["date"] == "2026-01-15"
    assert d["signal"] == "BUY"
    assert d["portfolio_value"] == 100000.0


def test_backtest_result():
    steps = [
        BacktestStep("2026-01-01", "BUY", 100000.0, 80000.0, 20000.0, {"action": "buy", "qty": 100}),
        BacktestStep("2026-02-01", "SELL", 105000.0, 100000.0, 5000.0, {"action": "sell", "qty": 100}),
        BacktestStep("2026-03-01", "HOLD", 110000.0, 100000.0, 10000.0, {}),
    ]
    result = BacktestResult("AAPL", "2026-01-01", "2026-03-01", steps, 100000.0)
    assert result.ticker == "AAPL"
    assert len(result.steps) == 3
    assert result.equity_curve == [100000.0, 100000.0, 105000.0, 110000.0]
    assert len(result.trades) == 2


def test_signal_to_action():
    m = MIDAS()
    assert m._signal_to_action("STRONG_BUY") == "buy"
    assert m._signal_to_action("BUY") == "buy"
    assert m._signal_to_action("buy") == "buy"
    assert m._signal_to_action("STRONG_SELL") == "sell"
    assert m._signal_to_action("SELL") == "sell"
    assert m._signal_to_action("HOLD") == "hold"
    assert m._signal_to_action("NEUTRAL") == "hold"
    assert m._signal_to_action("") == "hold"


def test_generate_dates():
    m = MIDAS()
    dates = m._generate_dates("2026-01-01", "2026-01-31", 10)
    assert len(dates) == 4
    assert dates[0] == "2026-01-01"
    assert dates[1] == "2026-01-11"
    assert dates[2] == "2026-01-21"
    assert dates[3] == "2026-01-31"


def test_generate_dates_single():
    m = MIDAS()
    dates = m._generate_dates("2026-06-01", "2026-06-01", 30)
    assert len(dates) == 1
    assert dates[0] == "2026-06-01"


def test_generate_dates_bad_input():
    m = MIDAS()
    dates = m._generate_dates("bad-date", "2026-06-01", 30)
    assert dates == []


def test_run_with_custom_signal():
    m = MIDAS(initial_cash=100000)
    def dummy_signal(ticker, date):
        return "BUY" if date < "2026-06-15" else "SELL"
    result = m.run("AAPL", "2026-06-01", "2026-06-30", interval_days=7,
                   signal_func=dummy_signal)
    assert result.ticker == "AAPL"
    assert len(result.steps) >= 3
    assert result.metrics is not None
