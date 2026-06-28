"""T.R.E.N.D. — Streamlit monitoring dashboard.

Displays live provider health, equity curves, portfolio state,
and backtest results in a single-pane glassmorphism UI.
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import streamlit as st
import pandas as pd
import yfinance as yf

from trading.monitoring.trend import TREND
from trading.portfolio.arcane import ARCANE
from trading.backtesting.metrics import compute_metrics, compute_trade_metrics
from trading.ticker_universe import get_all_tickers, format_ticker_display
from trading.dataflows.world_bank import get_macro_economic_data

try:  # noqa: E402
    from langchain_core.messages import HumanMessage
    from trading.llm_clients import create_llm_client
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

st.set_page_config(
    page_title="T.R.E.N.D. Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

DARK_CSS = """
<style>
    .main > div { padding: 1rem 2rem; }
    .stApp { background: #0a0a0f; color: #e0e0e0; }
    h1, h2, h3 { color: #00d4aa; }
    .metric-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.5rem 0;
        backdrop-filter: blur(8px);
    }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: #00d4aa; }
    .metric-label { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
    .stDataFrame { background: transparent; }
    .stAlert { border-radius: 8px; }
</style>
"""


def load_trend_state() -> TREND:
    state_path = Path("~/.trading/trend_state.json").expanduser()
    if state_path.exists():
        try:
            data = json.loads(state_path.read_text())
            trend = TREND(config=data.get("config", {}))
            for rec in data.get("records", []):
                trend.record_call(**rec)
            return trend
        except Exception:
            pass
    return TREND()


def save_trend_state(trend: TREND):
    state_dir = Path("~/.trading").expanduser()
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "trend_state.json"
    state_path.write_text(json.dumps(trend.to_dict(), indent=2))


def load_portfolio() -> Optional[ARCANE]:
    try:
        return ARCANE()
    except Exception:
        return None


def render_provider_health(trend: TREND):
    st.subheader("Provider Health")
    try:
        summary = trend.get_summary()
    except Exception:
        st.warning("Provider health data unavailable")
        return
    provider_stats = summary.get("provider_stats", []) if isinstance(summary, dict) else []
    if not provider_stats:
        st.info("No provider data yet. Make an analysis call first.")
        return
    cols = st.columns(len(provider_stats))
    for i, stat in enumerate(provider_stats):
        with cols[i]:
            is_active = stat.get("provider", "") == summary.get("current_provider", "")
            status = "● ACTIVE" if is_active else "○ STANDBY"
            color = "#00d4aa" if is_active else "#666"
            prov_name = stat.get("provider", "?").upper() if isinstance(stat, dict) else "?"
            calls = stat.get("calls", 0) if isinstance(stat, dict) else 0
            sr = stat.get("success_rate", 0.0) if isinstance(stat, dict) else 0.0
            avg = stat.get("avg_duration_ms", 0) if isinstance(stat, dict) else 0
            toks = stat.get("total_tokens", 0) if isinstance(stat, dict) else 0
            pct = f"{sr * 100:.0f}%" if isinstance(sr, (int, float)) else "0%"
            avg_ms = f"{avg:.0f}ms" if isinstance(avg, (int, float)) else "0ms"
            st.markdown(
                f'<div class="metric-card" style="border-color: {color}">'
                f'<div class="metric-label">{prov_name}</div>'
                f'<div class="metric-value" style="font-size:1rem;color:{color}">{status}</div>'
                f'<div style="margin-top:8px">Calls: {calls}</div>'
                f"<div>Success: {pct}</div>"
                f"<div>Avg: {avg_ms}</div>"
                f"<div>Tokens: {toks}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


def render_portfolio(arcane: Optional[ARCANE]):
    st.subheader("Portfolio")
    if not arcane:
        st.info("No portfolio data loaded")
        return
    metrics = arcane.get_performance_metrics()
    cols = st.columns(4)
    labels = [
        ("Total Value", f"${metrics.get('total_value', 0):,.0f}"),
        ("Cash", f"${metrics.get('cash', 0):,.0f}"),
        ("Return", f"{metrics.get('total_return_pct', 0)}%"),
        ("Drawdown", f"{metrics.get('trailing_drawdown', 0)*100:.1f}%"),
    ]
    for col, (label, value) in zip(cols, labels):
        with col:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-label">{label}</div>'
                f'<div class="metric-value">{value}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )


def render_backtest():
    st.subheader("Backtest Viewer")
    results_dir = Path("~/.trading/backtest_results").expanduser()
    results_dir.mkdir(parents=True, exist_ok=True)
    result_files = sorted(results_dir.glob("*.json"), reverse=True)

    # --- Inline runner ---
    with st.expander("Run a backtest", expanded=not bool(result_files)):
        bt_ticker = st.text_input("Ticker", value="AAPL", key="bt_ticker", placeholder="e.g. AAPL, MSFT")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            bt_from = st.text_input("Start date", value="2020-01-01", key="bt_from")
        with col_b:
            bt_to = st.text_input("End date", value=datetime.now().strftime("%Y-%m-%d"), key="bt_to")
        with col_c:
            bt_cash = st.number_input("Initial cash ($)", value=10_000_000, step=1_000_000, key="bt_cash")
        if st.button("Run Backtest", type="primary", key="bt_run"):
            from trading.backtesting.midas import MIDAS
            with st.spinner(f"Running backtest for {bt_ticker.strip().upper()}..."):
                try:
                    engine = MIDAS(initial_cash=float(bt_cash))
                    result = engine.run(bt_ticker.strip().upper(), bt_from, bt_to)
                    slug = f"{bt_ticker.strip().upper()}_{bt_from}_{bt_to}".replace(".", "_")
                    (results_dir / f"{slug}.json").write_text(json.dumps(result.to_dict(), indent=2))
                    st.session_state.bt_last_result = {
                        "ticker": bt_ticker.strip().upper(),
                        "from": bt_from,
                        "to": bt_to,
                        "steps": len(result.steps),
                        "equity": list(result.equity_curve),
                        "trades": list(result.trades),
                        "metrics": dict(result.metrics),
                        "trade_metrics": dict(result.trade_metrics),
                    }
                except Exception as e:
                    st.error(f"Backtest failed: {e}")
                    import traceback
                    st.code(traceback.format_exc(), language="python")

    # --- Display last inline result ---
    bt_last = st.session_state.get("bt_last_result")
    if bt_last:
        st.markdown("---")
        st.markdown(f"**{bt_last['ticker']}** — {bt_last['from']} → {bt_last['to']} ({bt_last['steps']} steps)")
        m = bt_last["metrics"]
        tm = bt_last["trade_metrics"]
        cols = st.columns(4)
        for i, (label, val) in enumerate([
            ("Return", f"{m.get('total_return_pct', '?')}%"),
            ("CAGR", f"{m.get('cagr_pct', '?')}%"),
            ("Sharpe", str(m.get('sharpe_ratio', '?'))),
            ("Max DD", f"{m.get('max_drawdown_pct', '?')}%"),
            ("Trades", str(tm.get('num_trades', 0))),
            ("Win Rate", f"{tm.get('win_rate', 0)}%"),
            ("Profit Factor", str(tm.get('profit_factor', 0))),
            ("Final Value", f"${m.get('final_value', 0):,.0f}"),
        ]):
            with cols[i % 4]:
                st.metric(label, val)
        eq = bt_last["equity"]
        if len(eq) > 1:
            st.line_chart(pd.DataFrame({"equity": eq}))
        with st.expander("Raw data"):
            st.json(bt_last)

    # --- Saved results ---
    if result_files:
        st.markdown("---")
        selected = st.selectbox("Select saved result", [f.name for f in result_files])
        if selected:
            path = results_dir / selected
            try:
                data = json.loads(path.read_text())
                equity = data.get("equity_curve") or []
                trades = data.get("trades") or []
                steps = data.get("steps") or []
                if not equity and steps:
                    equity = [data.get("initial_cash", 100000)] + [s.get("portfolio_value", 0) for s in steps]
                if not trades and steps:
                    trades = [s.get("trade", {}) for s in steps if s.get("trade", {}).get("action") in ("buy", "sell")]
                if equity:
                    metrics = compute_metrics(equity)
                    trade_met = compute_trade_metrics(trades) if trades else {"num_trades": 0, "win_rate": 0, "profit_factor": 0, "total_pnl": 0, "avg_win": 0, "avg_loss": 0}
                    st.markdown(f"**{data.get('ticker', '?')}** — {data.get('start_date', '?')} → {data.get('end_date', '?')}")
                    cols = st.columns(4)
                    for i, (label, val) in enumerate([
                        ("Return", f"{metrics.get('total_return_pct', '?')}%"),
                        ("CAGR", f"{metrics.get('cagr_pct', '?')}%"),
                        ("Sharpe", str(metrics.get('sharpe_ratio', '?'))),
                        ("Max DD", f"{metrics.get('max_drawdown_pct', '?')}%"),
                        ("Trades", str(trade_met.get('num_trades', 0))),
                        ("Win Rate", f"{trade_met.get('win_rate', 0)}%"),
                        ("Profit Factor", str(trade_met.get('profit_factor', 0))),
                        ("Final Value", f"${metrics.get('final_value', 0):,.0f}"),
                    ]):
                        with cols[i % 4]:
                            st.metric(label, val)
                    if len(equity) > 1:
                        st.line_chart(pd.DataFrame({"equity": equity}))
                    with st.expander("Raw data"):
                        st.json(data)
            except (json.JSONDecodeError, KeyError) as e:
                st.error(f"Failed to load backtest result: {e}")


def render_live_trading():
    st.subheader("Live Trading")
    state_path = Path("~/.trading/live_state.json").expanduser()
    if not state_path.exists():
        st.info("No live trading data. Run `trading run AAPL` to start.")
        return
    try:
        data = json.loads(state_path.read_text())
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Portfolio Value", f"${data.get('portfolio_value', 0):,.0f}")
        with col2:
            st.metric("Cash", f"${data.get('cash', 0):,.0f}")
        with col3:
            st.metric("Orders Filled", data.get("orders", 0))
        positions = data.get("positions", [])
        if positions:
            st.markdown("**Positions**")
            pos_data = pd.DataFrame(positions)
            st.dataframe(pos_data, use_container_width=True)
        else:
            st.info("No open positions")
    except Exception as e:
        st.error(f"Failed to load live state: {e}")


def _detect_available_providers() -> list[tuple[str, str]]:
    providers = []
    if os.environ.get("OPENAI_API_KEY"):
        providers.append(("openai", "gpt-5.4-mini"))
    if os.environ.get("ANTHROPIC_API_KEY"):
        providers.append(("anthropic", "claude-3-haiku-20240307"))
    if os.environ.get("GOOGLE_API_KEY"):
        providers.append(("google", "gemini-2.0-flash-lite"))
    return providers


def _fetch_ticker_snapshot(ticker: str) -> str:
    """Fetch recent price + volume data for a ticker. Returns a formatted string or empty on failure."""
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1mo")
        if hist.empty:
            return ""
        last = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else last
        first = hist.iloc[0]
        change_1d = last["Close"] - prev["Close"]
        change_1d_pct = (change_1d / prev["Close"]) * 100
        change_1m_pct = ((last["Close"] - first["Close"]) / first["Close"]) * 100
        high_1m = hist["High"].max()
        low_1m = hist["Low"].min()
        avg_vol = hist["Volume"].mean()
        return (
            f"Price: ${last['Close']:.2f}  |  "
            f"1d: {change_1d_pct:+.2f}% ({change_1d:+.2f})  |  "
            f"1m: {change_1m_pct:+.2f}%\n"
            f"1m High: ${high_1m:.2f}  |  "
            f"1m Low: ${low_1m:.2f}\n"
            f"Volume: {last['Volume']:,.0f}  |  "
            f"Avg Volume (1m): {avg_vol:,.0f}"
        )
    except Exception:
        return ""


def render_quick_analysis(trend: TREND):
    st.subheader("Quick Analysis")
    if not HAS_LLM:
        st.warning("LLM provider packages not installed. Run `pip install langchain-openai` and add your API key.")
        return

    available = _detect_available_providers()
    if not available:
        st.info("No API keys configured. Set OPENAI_API_KEY (or ANTHROPIC_API_KEY / GOOGLE_API_KEY) in Streamlit Secrets or .env to run live analysis.")
        return

    if "ticker_universe" not in st.session_state:
        with st.spinner("Loading ticker universe..."):
            universe = get_all_tickers()
            st.session_state.ticker_universe = universe
            browse = sorted(
                [f"{t['name']} ({t.get('exchange', '')}) — {t['ticker']}" for t in universe],
                key=lambda s: s.lower(),
            )
            st.session_state.ticker_browse_labels = browse
            st.session_state.ticker_browse_map = {}
            for t in universe:
                lbl = f"{t['name']} ({t.get('exchange', '')}) — {t['ticker']}"
                st.session_state.ticker_browse_map[lbl] = t["ticker"]
    browse_labels = st.session_state.ticker_browse_labels
    browse_map = st.session_state.ticker_browse_map

    search_q = st.text_input("Search ticker or company", placeholder="e.g. Apple, MSFT, Reliance...", key="ticker_search")
    q = search_q.strip()
    if q:
        ul = q.upper()
        matched = [lbl for lbl in browse_labels if ul in lbl.upper()]
        shown = matched[:250] if matched else ["— No matches —"]
    else:
        shown = browse_labels[:250]
    selected_lbl = st.selectbox("Select a ticker", shown, index=0, key="analysis_ticker")
    ticker = browse_map.get(selected_lbl) or q.upper()

    if q and not any(ticker in lbl for lbl in browse_labels):
        st.caption("⚠️ Ticker not found in universe")

    col2, col3 = st.columns([2, 1])
    with col2:
        provider_opts = {f"{p[0].upper()} ({p[1]})": p for p in available}
        default_prov = list(provider_opts.keys())[0]
        prov_choice = st.selectbox("Provider", list(provider_opts.keys()), index=0, key="analysis_provider")
    with col3:
        run = st.button("Analyze", type="primary", use_container_width=True)

    if run and ticker.strip():
        provider, model = provider_opts[prov_choice]
        start = time.time()
        with st.spinner(f"Fetching data for {ticker.upper()}..."):
            snapshot = _fetch_ticker_snapshot(ticker)
            macro = get_macro_economic_data(ticker, years=5, indicators="GDP, GDP growth, Inflation, Unemployment")
        with st.spinner(f"Analyzing {ticker.upper()} via {provider}..."):
            try:
                client = create_llm_client(provider=provider, model=model)
                llm = client.get_llm()
                data_block = ""
                if snapshot:
                    data_block += f"\nLive market data:\n{snapshot}\n"
                if macro and "No data" not in macro and "Could not" not in macro:
                    data_block += f"\nMacroeconomic context:\n{macro}\n"
                prompt = (
                    f"You are a professional stock analyst. Analyze {ticker.upper()} "
                    f"as of {datetime.now().strftime('%Y-%m-%d')}.{data_block}"
                    f"Provide a concise summary covering: 1) Recent price action, "
                    f"2) Key support/resistance levels, 3) Bull case, 4) Bear case, "
                    f"5) Overall signal (STRONG BUY / BUY / HOLD / SELL / STRONG SELL). "
                    f"Keep it under 200 words."
                )
                result = llm.invoke([HumanMessage(content=prompt)])
                duration_ms = int((time.time() - start) * 1000)
                text = result.content if hasattr(result, "content") else str(result)
                token_count = getattr(result, "usage_metadata", {}).get("total_tokens", 0) or 0

                trend.record_call(
                    provider=provider,
                    model=model,
                    duration_ms=duration_ms,
                    success=True,
                    token_count=token_count,
                )
                st.success(f"Analysis complete ({duration_ms}ms, {token_count} tokens)")
                if snapshot:
                    st.markdown("**Live Data**")
                    st.code(snapshot)
                if macro and "No data" not in macro and "Could not" not in macro:
                    st.markdown("**Macroeconomic Context (World Bank)**")
                    st.code(macro)
                st.markdown(f"**{ticker.upper()} Analysis**")
                st.markdown(text)
            except Exception as e:
                duration_ms = int((time.time() - start) * 1000)
                trend.record_call(
                    provider=provider,
                    model=model,
                    duration_ms=duration_ms,
                    success=False,
                    error=str(e),
                )
                st.error(f"Analysis failed: {e}")


def render_recent_calls(trend: TREND):
    st.subheader("Recent LLM Calls")
    records = trend.records[-20:][::-1]
    if not records:
        st.info("No LLM calls recorded yet")
        return
    data = [
        {
            "Time": r.timestamp[-19:-7] if len(r.timestamp) > 19 else r.timestamp,
            "Provider": r.provider,
            "Model": r.model,
            "Status": "✅" if r.success else "❌",
            "Duration": f"{r.duration_ms:.0f}ms",
            "Tokens": r.token_count,
        }
        for r in records
    ]
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)


def run_dashboard(host: str = "0.0.0.0", port: int = 8501):
    try:
        trend = load_trend_state()
    except Exception:
        trend = TREND()
        st.warning("Failed to load trend state, using defaults")
    try:
        arcane = load_portfolio()
    except Exception:
        arcane = None

    st.markdown(DARK_CSS, unsafe_allow_html=True)
    st.title("T.R.E.N.D. — Tactical Rick-Evaluation and Network Directed-trading")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    with st.sidebar:
        st.markdown("### Configuration")
        available = _detect_available_providers()
        if available:
            for prov, model in available:
                st.success(f"✅ {prov.upper()} ({model})")
        else:
            st.warning("No API keys configured")
        if "ticker_universe" in st.session_state:
            count = len(st.session_state.ticker_universe)
            ticker_str = f"| {count:,} tickers loaded"
            if count > 10000:
                ticker_str += " (US + EU + IN)"
            st.caption(ticker_str)
        st.divider()
        st.markdown("### Quickstart")
        st.code("trading analyze AAPL")
        st.code("trading run AAPL --loop")
        st.code("trading backtest AAPL --from 2020-01-01  # defaults to present")
        st.markdown("[GitHub](https://github.com/gauravsengar24/SuperPower) • [Docs](https://github.com/gauravsengar24/SuperPower/blob/main/TRADING.md)")

    sections = [
        ("Quick Analysis", lambda: render_quick_analysis(trend)),
        ("Live Trading", lambda: render_live_trading()),
        ("Provider Health", lambda: render_provider_health(trend)),
        ("Portfolio", lambda: render_portfolio(arcane)),
        ("Backtest Viewer", lambda: render_backtest()),
        ("Recent LLM Calls", lambda: render_recent_calls(trend)),
    ]
    for i, (name, render_fn) in enumerate(sections):
        try:
            if i > 0:
                st.divider()
            render_fn()
        except Exception as e:
            st.error(f"{name} unavailable: {e}")
            import traceback
            st.code(traceback.format_exc(), language="python")

    try:
        save_trend_state(trend)
    except Exception:
        pass


if __name__ == "__main__":
    run_dashboard()
