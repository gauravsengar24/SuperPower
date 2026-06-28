"""SuperTrading AI — CLI Entry Point.

Usage:
    trading analyze --ticker AAPL --date 2026-01-15
    trading dashboard
    trading backtest --ticker AAPL --from 2020-01-01  # --to defaults to today
    trading portfolio
    trading --help
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel

cli = typer.Typer(help="SuperTrading AI — Multi-Agent Trading Platform")
console = Console()

_ANALYST_NAMES = {
    "market": "Market/Technical",
    "social": "Sentiment/Social Media",
    "news": "News/Macro",
    "fundamentals": "Fundamentals",
}


@cli.command()
def analyze(
    ticker: str = typer.Argument(..., help="Ticker symbol to analyze"),
    date: str = typer.Option(
        datetime.now().strftime("%Y-%m-%d"),
        "--date", "-d",
        help="Analysis date (YYYY-MM-DD)",
    ),
    provider: str = typer.Option("openai", "--provider", "-p", help="LLM provider"),
    deep_llm: str = typer.Option("gpt-5.5", "--deep-llm", help="Deep thinking model"),
    quick_llm: str = typer.Option("gpt-5.4-mini", "--quick-llm", help="Quick thinking model"),
    debate_rounds: int = typer.Option(1, "--debate-rounds", help="Max debate rounds"),
    risk_rounds: int = typer.Option(1, "--risk-rounds", help="Max risk discussion rounds"),
    analysts: str = typer.Option("all", "--analysts", help="Analysts: all,market,social,news,fundamentals"),
    checkpoint: bool = typer.Option(False, "--checkpoint", help="Enable checkpoint resume"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save path for reports"),
):
    """Run the full MATRIX analysis pipeline on a ticker."""
    from trading.default_config import DEFAULT_CONFIG
    from trading.graph.trading_graph import TradingAgentsGraph

    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = provider
    config["deep_think_llm"] = deep_llm
    config["quick_think_llm"] = quick_llm
    config["max_debate_rounds"] = debate_rounds
    config["max_risk_discuss_rounds"] = risk_rounds
    config["checkpoint_enabled"] = checkpoint

    analyst_list = _parse_analysts(analysts)
    console.print(Panel(f"[bold]MATRIX Analysis:[/bold] {ticker} on {date}", expand=False))

    ta = TradingAgentsGraph(
        selected_analysts=analyst_list,
        debug=True,
        config=config,
    )

    try:
        final_state, signal = ta.propagate(ticker, date)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold green]Signal:[/bold green] {signal}")
    console.print(
        Panel(
            final_state.get("final_trade_decision", "No decision"),
            title="Final Trade Decision",
        )
    )

    save_path = output or config["results_dir"]
    report_path = ta.save_reports(final_state, ticker, Path(save_path))
    console.print(f"\n[dim]Reports saved: {report_path}[/dim]")


@cli.command()
def backtest(
    ticker: str = typer.Argument(..., help="Ticker to backtest"),
    from_date: str = typer.Option("2020-01-01", "--from", "-f", help="Start date"),
    to_date: str = typer.Option(
        datetime.now().strftime("%Y-%m-%d"), "--to", "-t",
        help="End date (default: today)",
    ),
    interval: int = typer.Option(30, "--interval", "-i", help="Days between analyses"),
    cash: float = typer.Option(100000.0, "--cash", "-c", help="Initial cash"),
    max_positions: int = typer.Option(10, "--max-positions", help="AEGIS max positions"),
    risk_per_trade: float = typer.Option(0.02, "--risk-per-trade", help="Risk per trade (pct)"),
):
    """Run M.I.D.A.S. backtesting — test strategy across historical window."""
    from trading.backtesting.midas import MIDAS

    console.print(f"[bold]M.I.D.A.S. Backtest:[/bold] {ticker} {from_date} \u2192 {to_date}")
    console.print(f"  Initial cash: ${cash:,.0f} | Interval: {interval}d")

    aegis_config = {
        "max_positions": max_positions,
        "default_risk_per_trade": risk_per_trade,
    }

    engine = MIDAS(initial_cash=cash, aegis_config=aegis_config)

    with console.status("[bold green]Running backtest...[/bold green]") as status:
        result = engine.run(ticker, from_date, to_date,
                            interval_days=interval)

    console.print()
    m = result.metrics
    tm = result.trade_metrics
    table = Table(title=f"M.I.D.A.S. Results — {ticker}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Total Return", f"{m['total_return_pct']}%")
    table.add_row("CAGR", f"{m['cagr_pct']}%")
    table.add_row("Sharpe Ratio", str(m['sharpe_ratio']))
    table.add_row("Sortino Ratio", str(m['sortino_ratio']))
    table.add_row("Max Drawdown", f"{m['max_drawdown_pct']}%")
    table.add_row("Volatility", f"{m['volatility_pct']}%")
    table.add_row("Trades", str(tm['num_trades']))
    table.add_row("Win Rate", f"{tm['win_rate']}%")
    table.add_row("Profit Factor", str(tm['profit_factor']))
    table.add_row("Final Value", f"${m['final_value']:,.2f}")
    console.print(table)


@cli.command()
def dashboard(
    port: int = typer.Option(8501, "--port", "-p", help="Dashboard port"),
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Dashboard host"),
):
    """Launch the T.R.E.N.D. monitoring dashboard."""
    console.print(f"[bold]T.R.E.N.D. Dashboard:[/bold] http://{host}:{port}")
    from trading.monitoring.dashboard import run_dashboard
    run_dashboard(host=host, port=port)


@cli.command()
def portfolio():
    """Show A.R.C.A.N.E. portfolio status."""
    from trading.portfolio.arcane import ARCANE
    arcane = ARCANE()

    metrics = arcane.get_performance_metrics()
    table = Table(title="Portfolio Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    for key, value in metrics.items():
        table.add_row(key.replace("_", " ").title(), str(value))
    console.print(table)


@cli.command()
def version():
    """Show version."""
    from trading import __version__
    console.print(f"SuperTrading AI v{__version__}")
    console.print("https://github.com/gauravsengar24/SuperPower")


def _parse_analysts(analysts_str: str) -> tuple:
    if analysts_str.lower() == "all":
        return ("market", "social", "news", "fundamentals")
    parts = [a.strip().lower() for a in analysts_str.split(",")]
    valid = {"market", "social", "news", "fundamentals"}
    return tuple(a for a in parts if a in valid)


if __name__ == "__main__":
    cli()
