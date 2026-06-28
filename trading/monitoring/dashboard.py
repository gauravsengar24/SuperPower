"""T.R.E.N.D. — Streamlit monitoring dashboard.

Displays live provider health, equity curves, portfolio state,
and backtest results in a single-pane glassmorphism UI.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import streamlit as st
import pandas as pd

from trading.monitoring.trend import TREND
from trading.portfolio.arcane import ARCANE
from trading.backtesting.metrics import compute_metrics, compute_trade_metrics

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
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    return TREND()


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
    trend = load_trend_state()
    arcane = load_portfolio()

    st.markdown(DARK_CSS, unsafe_allow_html=True)
    st.title("T.R.E.N.D. — Tactical Rick-Evaluation and Network Directed-trading")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    render_provider_health(trend)
    st.divider()
    render_portfolio(arcane)
    st.divider()
    render_backtest()
    st.divider()
    render_recent_calls(trend)


if __name__ == "__main__":
    run_dashboard()
