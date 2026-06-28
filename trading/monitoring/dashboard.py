"""T.R.E.N.D. — Streamlit monitoring dashboard.

Displays live provider health, equity curves, portfolio state,
and backtest results in a single-pane glassmorphism UI.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st
import pandas as pd

from trading.monitoring.trend import TREND
from trading.portfolio.arcane import ARCANE
from trading.backtesting.metrics import compute_metrics, compute_trade_metrics
from trading.ticker_universe import get_all_tickers, format_ticker_display

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
    if not results_dir.exists():
        st.info("No backtest results found. Run `trading backtest` first.")
        return
    result_files = sorted(results_dir.glob("*.json"), reverse=True)
    if not result_files:
        st.info("No backtest results found.")
        return

    selected = st.selectbox(
        "Select backtest result",
        [f.name for f in result_files],
    )
    if selected:
        path = results_dir / selected
        try:
            data = json.loads(path.read_text())
            equity = data.get("equity_curve", [])
            trades = data.get("trades", [])
            if equity:
                metrics = compute_metrics(equity)
                trade_met = compute_trade_metrics(trades)
                st.markdown("**Metrics**")
                cols = st.columns(4)
                for col, (k, v) in zip(cols, list(metrics.items())[:4]):
                    with col:
                        st.metric(k.replace("_", " ").title(), v)
                if len(equity) > 1:
                    df = pd.DataFrame({"equity": equity})
                    st.line_chart(df)
        except (json.JSONDecodeError, KeyError):
            st.error("Failed to load backtest result")


def _detect_available_providers() -> list[tuple[str, str]]:
    providers = []
    if os.environ.get("OPENAI_API_KEY"):
        providers.append(("openai", "gpt-5.4-mini"))
    if os.environ.get("ANTHROPIC_API_KEY"):
        providers.append(("anthropic", "claude-3-haiku-20240307"))
    if os.environ.get("GOOGLE_API_KEY"):
        providers.append(("google", "gemini-2.0-flash-lite"))
    return providers


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
            st.session_state.ticker_universe = get_all_tickers()
            st.session_state.ticker_all_labels = [
                format_ticker_display(t) for t in st.session_state.ticker_universe
            ]
            st.session_state.ticker_all_map = {
                format_ticker_display(t): t["ticker"] for t in st.session_state.ticker_universe
            }
    ticker_all_labels = st.session_state.ticker_all_labels
    ticker_all_map = st.session_state.ticker_all_map

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        raw = st.text_input("Ticker", value="", placeholder="e.g. AAPL, MSFT, RELIANCE.NS...", key="analysis_ticker")
        ticker = raw.strip().upper()
        if ticker:
            matches = [lbl for lbl in ticker_all_labels if ticker in lbl.upper()]
            if len(matches) == 1:
                st.caption(f"✅ {matches[0]}")
            elif len(matches) > 1:
                st.caption(f"🔍 {len(matches)} matches — be more specific")
            else:
                st.caption("⚠️ Ticker not found in universe")
    with col2:
        provider_opts = {f"{p[0].upper()} ({p[1]})": p for p in available}
        default_prov = list(provider_opts.keys())[0]
        prov_choice = st.selectbox("Provider", list(provider_opts.keys()), index=0, key="analysis_provider")
    with col3:
        run = st.button("Analyze", type="primary", use_container_width=True)

    if run and ticker.strip():
        provider, model = provider_opts[prov_choice]
        start = time.time()
        with st.spinner(f"Analyzing {ticker.upper()} via {provider}..."):
            try:
                client = create_llm_client(provider=provider, model=model)
                llm = client.get_llm()
                prompt = (
                    f"You are a professional stock analyst. Analyze {ticker.upper()} "
                    f"as of {datetime.now().strftime('%Y-%m-%d')}. "
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
        st.code("trading backtest AAPL --from 2020-01-01 --to 2023-12-31")
        st.markdown("[GitHub](https://github.com/gauravsengar24/SuperPower) • [Docs](https://github.com/gauravsengar24/SuperPower/blob/main/TRADING.md)")

    sections = [
        ("Quick Analysis", lambda: render_quick_analysis(trend)),
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
