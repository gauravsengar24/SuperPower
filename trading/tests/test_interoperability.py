"""Phase 1+2 Interoperability Verification — tests that ALL modules work together."""

import os
import sys
from pathlib import Path

os.environ.pop("OPENAI_API_KEY", None)

print("=" * 60)
print("SUPERTRADING AI — INTEROPERABILITY VERIFICATION")
print("=" * 60)

# === Define all test functions first ===

def test_graph_init():
    from trading.default_config import DEFAULT_CONFIG
    from trading.dataflows.config import set_config
    from trading.graph.trading_graph import TradingAgentsGraph
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "openai"
    set_config(config)
    ta = TradingAgentsGraph(debug=True, config=config)
    assert list(ta.tool_nodes.keys()) == ["market", "social", "news", "fundamentals"]
    assert ta.memory_log.log_path is not None
    print(f"  ✅ Tool nodes: {list(ta.tool_nodes.keys())}")


def test_signal():
    from trading.graph.trading_graph import TradingAgentsGraph
    from trading.default_config import DEFAULT_CONFIG
    ta = TradingAgentsGraph(config=DEFAULT_CONFIG.copy())
    assert ta.process_signal("STRONG BUY") == "STRONG_BUY"
    assert ta.process_signal("BUY") == "BUY"
    assert ta.process_signal("HOLD") == "HOLD"
    assert ta.process_signal("SELL") == "SELL"
    assert ta.process_signal("STRONG SELL") == "STRONG_SELL"


def test_memory():
    from trading.default_config import DEFAULT_CONFIG
    config = DEFAULT_CONFIG.copy()
    config["memory_log_path"] = "/tmp/.trading_test_memory.md"
    from trading.agents.utils.memory import TradingMemoryLog
    log = TradingMemoryLog(config)
    log.store_decision("AAPL", "2026-01-15", "BUY")
    ctx = log.get_past_context("AAPL")
    assert len(ctx) > 0
    pending = log.get_pending_entries()
    assert len(pending) >= 1
    os.remove(config["memory_log_path"])


def test_state():
    from trading.graph.propagation import create_initial_state
    state = create_initial_state("AAPL", "2026-01-15")
    assert state["company_of_interest"] == "AAPL"
    assert state["trade_date"] == "2026-01-15"
    assert state["final_trade_decision"] == "HOLD"
    assert len(state) == 15


def test_analyst_chain():
    from unittest.mock import MagicMock
    from trading.graph.setup import run_simple_analyst_chain
    from trading.graph.propagation import create_initial_state
    from trading.default_config import DEFAULT_CONFIG
    from trading.dataflows.config import set_config
    from trading.graph.trading_graph import TradingAgentsGraph
    config = DEFAULT_CONFIG.copy()
    set_config(config)
    ta = TradingAgentsGraph(config=config)
    state = create_initial_state("AAPL", "2026-01-15")
    state["config"] = config
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = "BUY AAPL — strong momentum"
    result = run_simple_analyst_chain(
        state, ("market", "social", "news", "fundamentals"),
        mock_llm, mock_llm, ta.tool_nodes,
    )
    assert result["market_report"]
    assert result["sentiment_report"]
    assert result["news_report"]
    assert result["fundamentals_report"]
    print(f"  ✅ Reports: Mkt={bool(result['market_report'])} Soc={bool(result['sentiment_report'])} News={bool(result['news_report'])} Fund={bool(result['fundamentals_report'])}")
    print(f"  ✅ Decision: {result['final_trade_decision'][:80]}")
    assert len(result["final_trade_decision"]) > 0


def test_reporting():
    from trading.graph.trading_graph import TradingAgentsGraph
    from trading.default_config import DEFAULT_CONFIG
    from trading.graph.propagation import create_initial_state
    config = DEFAULT_CONFIG.copy()
    config["results_dir"] = "/tmp/.trading_test_reports"
    ta = TradingAgentsGraph(config=config)
    state = create_initial_state("AAPL", "2026-01-15")
    state["market_report"] = "Test market report"
    state["sentiment_report"] = "Test sentiment"
    state["news_report"] = "Test news"
    state["fundamentals_report"] = "Test fundamentals"
    state["final_trade_decision"] = "BUY — test"
    path = ta.save_reports(state, "AAPL", Path("/tmp/.trading_test_reports/test"))
    assert (path / "report.md").exists()
    assert (path / "summary.md").exists()
    assert (path / "market_analysis.md").exists()
    import shutil
    shutil.rmtree("/tmp/.trading_test_reports", ignore_errors=True)


def test_execution_chain():
    from trading.risk.aegis import AEGIS, PortfolioState, MarketSnapshot
    from trading.execution.velocity import VELOCITY
    from trading.broker.paper import HermesPaperBroker
    broker = HermesPaperBroker()
    broker.update_price("AAPL", 150.0)
    aegis = AEGIS()
    velo = VELOCITY(broker=broker, aegis=aegis)
    portfolio = PortfolioState(positions=[], cash=100000.0, total_value=100000.0, peak_value=100000.0, daily_start_value=100000.0, initial_value=100000.0)
    market = MarketSnapshot(ticker="AAPL", price=150.0, vix=15.0)
    report = velo.execute("AAPL", "buy", 10, "market",
                          portfolio_state=portfolio, market_snapshot=market)
    assert report.success
    assert report.order is not None
    assert report.order.status.name == "FILLED"
    print(f"  ✅ Order: {report.order.filled_qty} @ {report.order.avg_fill_price}")
    # AEGIS rejection test
    from dataclasses import dataclass
    @dataclass
    class DummyPos:
        ticker: str
        pnl: float = 0
        pnl_pct: float = 0
    portfolio_full = PortfolioState(
        positions=[DummyPos(f"T{i}") for i in range(10)],
        cash=0, total_value=1000, peak_value=1000,
        daily_start_value=1000, initial_value=1000,
    )
    aegis_block = AEGIS({"max_positions": 5})
    velo_block = VELOCITY(broker=broker, aegis=aegis_block)
    report2 = velo_block.execute("GOOGL", "buy", 10, "market",
                                  portfolio_state=portfolio_full,
                                  market_snapshot=MarketSnapshot(ticker="GOOGL", price=180.0, vix=15.0))
    assert not report2.success
    assert "AEGIS" in report2.message
    print(f"  ✅ AEGIS rejected over-positioned trade: {report2.message[:60]}")


def test_portfolio():
    from trading.portfolio.arcane import ARCANE
    from trading.broker.base import Order, OrderSide, OrderType, OrderStatus
    arcane = ARCANE(state_path="/tmp/.trading_test_portfolio.json")
    order = Order(
        id="test1", ticker="AAPL", side=OrderSide.BUY,
        order_type=OrderType.MARKET, qty=10, filled_qty=10,
        avg_fill_price=150.0, status=OrderStatus.FILLED,
    )
    arcane.record_order(order)
    metrics = arcane.get_performance_metrics()
    assert metrics["num_positions"] == 1
    assert metrics["trade_count"] == 1
    os.remove("/tmp/.trading_test_portfolio.json")
    # Multi-trade
    arcane2 = ARCANE(state_path="/tmp/.trading_test_portfolio2.json")
    arcane2.record_order(order)
    sell_order = Order(
        id="test2", ticker="AAPL", side=OrderSide.SELL,
        order_type=OrderType.MARKET, qty=10, filled_qty=10,
        avg_fill_price=155.0, status=OrderStatus.FILLED,
    )
    arcane2.record_order(sell_order)
    m2 = arcane2.get_performance_metrics()
    assert m2["num_positions"] == 0
    assert m2["trade_count"] == 2
    assert m2["total_value"] > 100000.0
    os.remove("/tmp/.trading_test_portfolio2.json")


def test_trend():
    from trading.monitoring.trend import TREND
    trend = TREND()
    trend.record_call("openai", "gpt-5.5", 1200, True, 500)
    trend.record_call("openai", "gpt-5.5", 800, True, 300)
    trend.record_call("openai", "gpt-5.5", 0, False, error="timeout")
    trend.record_call("openai", "gpt-5.5", 0, False, error="timeout")
    trend.record_call("openai", "gpt-5.5", 0, False, error="timeout")
    summary = trend.get_summary()
    assert summary["total_calls"] == 5
    assert summary["total_errors"] == 3
    assert summary["current_provider"] != "openai"
    print(f"  \u2705 Fallback: {summary['current_provider']} after {summary['total_errors']} errors")


def test_cli():
    from typer.testing import CliRunner
    from trading.cli.main import cli
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "SuperTrading AI" in result.output
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "SuperTrading AI" in result.output
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "analyze" in result.output


def test_symbols():
    from trading.dataflows.symbol_utils import normalize_symbol, is_yahoo_safe, safe_ticker_component
    assert normalize_symbol("BTC") == "BTC-USD"
    assert is_yahoo_safe("AAPL")
    assert not is_yahoo_safe("../etc/passwd")
    assert safe_ticker_component("AAPL") == "AAPL"
    assert safe_ticker_component("../exploit") == ".._EXPLOIT"


def test_config_env_overrides():
    from trading.default_config import DEFAULT_CONFIG
    os.environ["TRADING_MAX_POSITIONS"] = "5"
    os.environ["TRADING_TEMPERATURE"] = "0.3"
    # Reload config (env overrides are applied at import time)
    import importlib
    import trading.default_config
    importlib.reload(trading.default_config)
    from trading.default_config import DEFAULT_CONFIG as cfg
    assert cfg.get("max_positions") == 5
    assert cfg.get("temperature") == 0.3
    del os.environ["TRADING_MAX_POSITIONS"]
    del os.environ["TRADING_TEMPERATURE"]


tests = [
    ("5a", "Graph instantiation (no API key)", test_graph_init),
    ("5b", "Signal processing", test_signal),
    ("5c", "Memory log persistence", test_memory),
    ("5d", "Initial state creation", test_state),
    ("5e", "Analyst chain with mocked LLM", test_analyst_chain),
    ("5f", "Report writing", test_reporting),
    ("5g", "AEGIS + VELOCITY + Hermes", test_execution_chain),
    ("5h", "ARCANE portfolio management", test_portfolio),
    ("5i", "TREND provider monitoring", test_trend),
    ("5j", "CLI commands", test_cli),
    ("5k", "Symbol utilities + path safety", test_symbols),
    ("5l", "Config env-var overrides", test_config_env_overrides),
]

passed = 0
failed = 0
for num, name, func in tests:
    try:
        func()
        print(f"  ✅ {num}: {name}")
        passed += 1
    except Exception as e:
        print(f"  ❌ {num}: {name} — {e}")
        import traceback
        traceback.print_exc()
        failed += 1

print()
print("=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
if failed:
    sys.exit(1)
print("ALL INTEROPERABILITY TESTS PASSED")
print("=" * 60)
