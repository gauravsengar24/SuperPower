"""T.R.E.N.D. — Streamlit monitoring dashboard.

Kitco-inspired dark financial terminal with glassmorphism cards,
gold accents, animated ticker tape, and full-width bento-grid layout.
"""

import contextlib
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st
import yfinance as yf

from trading.backtesting.metrics import compute_metrics, compute_trade_metrics
from trading.dataflows.world_bank import get_macro_economic_data
from trading.monitoring.trend import TREND
from trading.portfolio.arcane import ARCANE
from trading.ticker_universe import get_all_tickers

try:
    from langchain_core.messages import HumanMessage

    from trading.llm_clients import create_llm_client
    HAS_LLM = True
except ImportError:
    HAS_LLM = False

st.set_page_config(
    page_title="T.R.E.N.D. Dashboard",
    page_icon="\U0001f4c8",
    layout="wide",
    initial_sidebar_state="expanded",
)

KITCO_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    code, pre, .stCodeBlock, .mono { font-family: 'JetBrains Mono', 'SF Mono', monospace !important; }

    .stApp {
        background: #06060a;
        color: #f0f0f0;
    }

    .block-container {
        max-width: 100% !important;
        padding: 1rem 2.5rem !important;
    }

    @media (max-width: 1200px) {
        .block-container { padding: 0.8rem 1.2rem !important; }
    }

    h1, h2, h3 {
        font-weight: 600;
        letter-spacing: -0.02em;
    }

    h1 {
        color: #f0f0f0;
        font-size: 1.4rem;
    }

    h2 {
        color: #d4a843;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-top: 0 !important;
        padding: 0.6rem 0 0.3rem 0;
        border-bottom: 1px solid rgba(212,168,67,0.2);
    }

    h3 {
        color: #d4a843;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0e0e18; }
    ::-webkit-scrollbar-thumb { background: #2a2a3a; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #d4a843; }

    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
    }

    .stApp header { background: rgba(6,6,10,0.9) !important; backdrop-filter: blur(16px) !important; }

    .stButton button {
        background: linear-gradient(135deg, rgba(212,168,67,0.2), rgba(212,168,67,0.05)) !important;
        border: 1px solid rgba(212,168,67,0.3) !important;
        color: #d4a843 !important;
        font-weight: 600 !important;
        font-size: 0.75rem !important;
        border-radius: 8px !important;
        transition: all 200ms cubic-bezier(.16,1,.3,1) !important;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, rgba(212,168,67,0.35), rgba(212,168,67,0.1)) !important;
        border-color: #d4a843 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(212,168,67,0.15);
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #d4a843, #b8902a) !important;
        color: #06060a !important;
        border: none !important;
        font-weight: 700 !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #e8b830, #d4a843) !important;
        box-shadow: 0 4px 24px rgba(212,168,67,0.3);
    }

    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 8px !important;
        color: #f0f0f0 !important;
        font-size: 0.8rem !important;
        font-family: 'JetBrains Mono', monospace !important;
        transition: border-color 200ms ease;
    }
    .stTextInput input:focus, .stSelectbox div[data-baseweb="select"] > div:focus-within {
        border-color: rgba(212,168,67,0.5) !important;
        box-shadow: 0 0 0 2px rgba(212,168,67,0.1) !important;
    }

    div.stNumberInput input {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 8px !important;
        color: #f0f0f0 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    .stAlert { border-radius: 8px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); }
    .stAlert > div { color: #b0b0bc; }

    .stDataFrame { background: transparent !important; }
    .stDataFrame td, .stDataFrame th {
        background: transparent !important;
        color: #f0f0f0 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.7rem !important;
        border-bottom: 1px solid rgba(255,255,255,0.04) !important;
    }
    .stDataFrame th { color: #606070 !important; text-transform: uppercase; letter-spacing: 0.5px; font-size: 0.65rem !important; }

    div.stExpander {
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        overflow: hidden;
        transition: all 200ms cubic-bezier(.16,1,.3,1);
    }
    div.stExpander:hover { border-color: rgba(212,168,67,0.2); }
    div.stExpander summary { font-size: 0.8rem; font-weight: 600; color: #d4a843; }
    div.stExpander[aria-expanded="true"] { border-color: rgba(212,168,67,0.3); }

    .stSidebar {
        background: #0a0a14 !important;
        border-right: 1px solid rgba(255,255,255,0.04);
    }
    .stSidebar .stMarkdown h3 { color: #606070; font-size: 0.65rem; letter-spacing: 1.5px; }

    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(212,168,67,0.2), transparent);
        margin: 0.8rem 0;
    }

    .stProgress > div > div > div { background: #d4a843 !important; }

    @keyframes tickerScroll {
        0% { transform: translateX(0); }
        100% { transform: translateX(-50%); }
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    @keyframes fadeSlideUp {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes numberRoll {
        from { transform: translateY(8px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }

    .ticker-tape {
        overflow: hidden;
        white-space: nowrap;
        background: rgba(6,6,10,0.95);
        border-bottom: 1px solid rgba(212,168,67,0.15);
        padding: 0.5rem 0;
        margin: 0 -2.5rem;
        padding-left: 2.5rem;
        padding-right: 2.5rem;
        margin-bottom: 0.5rem;
    }
    .ticker-inner {
        display: inline-block;
        animation: tickerScroll 50s linear infinite;
        white-space: nowrap;
    }
    .ticker-inner:hover { animation-play-state: paused; }
    .ticker-item {
        display: inline-block;
        margin-right: 3rem;
        font-size: 0.85rem;
        font-family: 'JetBrains Mono', monospace;
        color: #b0b0bc;
    }
    .ticker-symbol { color: #f0f0f0; font-weight: 600; }
    .ticker-price { color: #f0f0f0; margin-left: 0.5rem; }
    .ticker-change { margin-left: 0.4rem; font-weight: 500; }
    .ticker-change.pos { color: #22c55e; }
    .ticker-change.neg { color: #ef4444; }

    .glass-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(10,10,20,0.8) 100%);
        backdrop-filter: blur(20px) saturate(210%);
        -webkit-backdrop-filter: blur(20px) saturate(210%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.04);
        transition: all 300ms cubic-bezier(.16,1,.3,1);
        animation: fadeSlideUp 0.4s ease-out both;
    }
    .glass-card:hover {
        border-color: rgba(212,168,67,0.25);
        box-shadow: 0 12px 40px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.08);
        transform: translateY(-2px);
    }
    .glass-card.gold {
        border-color: rgba(212,168,67,0.25);
        background: linear-gradient(135deg, rgba(212,168,67,0.06) 0%, rgba(10,10,20,0.8) 100%);
    }
    .glass-card.gold:hover {
        border-color: rgba(212,168,67,0.45);
        box-shadow: 0 12px 40px rgba(0,0,0,0.6), 0 0 24px rgba(212,168,67,0.06);
    }

    .metric-label {
        font-size: 0.7rem;
        color: #606070;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 500;
        margin-bottom: 0.1rem;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        color: #f0f0f0;
        line-height: 1.2;
        animation: numberRoll 0.5s ease-out both;
    }
    .metric-value.gold { color: #d4a843; }
    .metric-value.pos { color: #22c55e; }
    .metric-value.neg { color: #ef4444; }
    .metric-sub {
        font-size: 0.75rem;
        color: #606070;
        font-family: 'JetBrains Mono', monospace;
        margin-top: 0.2rem;
    }

    .led-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        vertical-align: middle;
    }
    .led-dot.active { background: #22c55e; box-shadow: 0 0 8px rgba(34,197,94,0.5); animation: pulse 1.2s infinite; }
    .led-dot.inactive { background: #606070; }
    .led-dot.error { background: #ef4444; box-shadow: 0 0 8px rgba(239,68,68,0.4); animation: pulse 0.8s infinite; }
    .led-dot.gold { background: #d4a843; box-shadow: 0 0 8px rgba(212,168,67,0.4); animation: pulse 1.5s infinite; }

    .data-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.45rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.03);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        transition: background 200ms ease;
    }
    .data-row:hover { background: rgba(255,255,255,0.03); }
    .data-row:last-child { border-bottom: none; }
    .data-row .label { color: #808090; }
    .data-row .value { color: #f0f0f0; font-weight: 500; }
    .data-row .value.pos { color: #22c55e; }
    .data-row .value.neg { color: #ef4444; }

    .section-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #d4a843;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        padding: 0.6rem 0 0.4rem 0;
        border-bottom: 1px solid rgba(212,168,67,0.15);
        margin-bottom: 0.8rem;
    }

    .st-emotion-cache-1jicfl2 { padding: 0 !important; }
    .main > div { padding: 0; }

    @media (max-width: 768px) {
        .block-container { padding: 0.5rem 1rem !important; }
        .ticker-tape { margin: 0 -1rem; padding-left: 1rem; padding-right: 1rem; }
        .ticker-item { font-size: 0.7rem; margin-right: 1.5rem; }
        .metric-value { font-size: 1.2rem; }
    }
</style>
"""

TICKER_WATCHLIST = [
    ("SPY", "S&P 500"), ("QQQ", "Nasdaq"), ("GLD", "Gold"),
    ("SLV", "Silver"), ("BTC-USD", "Bitcoin"), ("ETH-USD", "Ethereum"),
    ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("NVDA", "NVIDIA"),
    ("TSLA", "Tesla"), ("AMZN", "Amazon"), ("META", "Meta"),
]


def _fetch_ticker_prices() -> list[dict]:
    tickers = [t[0] for t in TICKER_WATCHLIST]
    try:
        data = yf.download(tickers, period="5d", auto_adjust=True, group_by="ticker")
        if data.empty:
            return _fallback_prices()
    except Exception:
        return _fallback_prices()

    rows = []
    for ticker in tickers:
        try:
            if isinstance(data.columns, pd.MultiIndex) and ticker in data.columns.levels[0]:
                closes = data[ticker]["Close"].dropna()
            else:
                closes = data["Close"].dropna() if "Close" in data.columns else pd.Series()
            if len(closes) < 2:
                continue
            price = float(closes.iloc[-1])
            prev = float(closes.iloc[-2])
            chg = price - prev
            chg_pct = (chg / prev) * 100
            idx = [t[0] for t in TICKER_WATCHLIST].index(ticker)
            rows.append({
                "symbol": TICKER_WATCHLIST[idx][0],
                "name": TICKER_WATCHLIST[idx][1],
                "price": price,
                "change": chg,
                "change_pct": chg_pct,
            })
        except (KeyError, IndexError, TypeError, ValueError):
            continue
    return rows or _fallback_prices()


def _fallback_prices() -> list[dict]:
    fallbacks = [
        (586.20, 2.10), (198.40, -0.80), (232.00, 1.50),
        (30.80, -0.25), (67800, 1200), (3450, 85),
        (218.50, 1.20), (425.30, -2.10), (875.00, 15.40),
        (248.60, -3.20), (198.20, 1.80), (535.00, 4.50),
    ]
    return [
        {"symbol": TICKER_WATCHLIST[i][0], "name": TICKER_WATCHLIST[i][1],
         "price": fv[0], "change": fv[1], "change_pct": (fv[1]/fv[0])*100}
        for i, fv in enumerate(fallbacks)
    ]


def render_ticker_tape():
    prices = _fetch_ticker_prices()
    items_html = ""
    for p in prices * 2:
        cls = "pos" if p["change"] >= 0 else "neg"
        arrow = "\u25b2" if p["change"] >= 0 else "\u25bc"
        items_html += (
            f'<span class="ticker-item">'
            f'<span class="ticker-symbol">{p["symbol"]}</span>'
            f'<span class="ticker-price">${p["price"]:,.2f}</span>'
            f'<span class="ticker-change {cls}">{arrow} {p["change_pct"]:+.2f}%</span>'
            f"</span>"
        )
    st.markdown(
        f'<div class="ticker-tape"><div class="ticker-inner">{items_html}</div></div>',
        unsafe_allow_html=True,
    )


def render_hero(arcane: Optional[ARCANE]):
    if not arcane:
        return
    metrics = arcane.get_performance_metrics()
    total = metrics.get("total_value", 0)
    ret = metrics.get("total_return_pct", 0)
    dd = metrics.get("trailing_drawdown", 0) * 100
    ret_cls = "pos" if ret >= 0 else "neg"
    ret_sign = "+" if ret >= 0 else ""

    st.markdown(
        f"""
        <div class="glass-card gold" style="margin-bottom:1rem;padding:1.5rem 2rem;animation-delay:0s;">
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1.5rem;">
                <div>
                    <div class="metric-label">Portfolio Value</div>
                    <div class="metric-value gold" style="font-size:2.6rem;">${total:,.0f}</div>
                </div>
                <div style="display:flex;gap:3rem;">
                    <div>
                        <div class="metric-label">Total Return</div>
                        <div class="metric-value {ret_cls}" style="font-size:1.6rem;">{ret_sign}{ret}%</div>
                    </div>
                    <div>
                        <div class="metric-label">Drawdown</div>
                        <div class="metric-value neg" style="font-size:1.6rem;">-{dd:.1f}%</div>
                    </div>
                    <div>
                        <div class="metric-label">Status</div>
                        <div style="margin-top:0.3rem;"><span class="led-dot active"></span><span style="color:#22c55e;font-size:0.85rem;font-weight:600;">LIVE</span></div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
        return ARCANE(config={"initial_cash": 10_000.0})
    except Exception:
        return None


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


def render_analysis_panel(trend: TREND):
    st.markdown('<div class="section-title">Quick Analysis</div>', unsafe_allow_html=True)
    if not HAS_LLM:
        st.warning("LLM packages not installed.")
        return
    available = _detect_available_providers()
    if not available:
        st.info("No API keys configured.")
        return

    if "ticker_universe" not in st.session_state:
        with st.spinner("Loading ticker universe..."):
            universe = get_all_tickers()
            st.session_state.ticker_universe = universe
            browse = sorted(
                [f"{t['name']} ({t.get('exchange', '')}) \u2014 {t['ticker']}" for t in universe],
                key=lambda s: s.lower(),
            )
            st.session_state.ticker_browse_labels = browse
            st.session_state.ticker_browse_map = {}
            for t in universe:
                lbl = f"{t['name']} ({t.get('exchange', '')}) \u2014 {t['ticker']}"
                st.session_state.ticker_browse_map[lbl] = t["ticker"]
    browse_labels = st.session_state.ticker_browse_labels
    browse_map = st.session_state.ticker_browse_map

    search_q = st.text_input("Search ticker", placeholder="Apple, MSFT, Reliance...", key="ticker_search")
    q = search_q.strip()
    if q:
        ul = q.upper()
        matched = [lbl for lbl in browse_labels if ul in lbl.upper()]
        shown = matched[:250] if matched else ["\u2014 No matches \u2014"]
    else:
        shown = browse_labels[:250]
    selected_lbl = st.selectbox("Select", shown, index=0, key="analysis_ticker")
    ticker = browse_map.get(selected_lbl) or q.upper()

    if q and not any(ticker in lbl for lbl in browse_labels):
        st.caption("\u26a0\ufe0f Not in universe")

    col_a, col_b = st.columns([2, 1])
    with col_a:
        provider_opts = {f"{p[0].upper()} ({p[1]})": p for p in available}
        prov_choice = st.selectbox("Provider", list(provider_opts.keys()), index=0, key="analysis_provider")
    with col_b:
        st.markdown("<br>", unsafe_allow_html=True)
        run = st.button("Analyze", type="primary", use_container_width=True)

    if run and ticker.strip():
        provider, model = provider_opts[prov_choice]
        start = time.time()
        with st.spinner(f"Fetching data for {ticker.upper()}..."):
            snapshot = _fetch_ticker_snapshot(ticker)
            macro = get_macro_economic_data(ticker, years=5, indicators="GDP, GDP growth, Inflation, Unemployment")
        with st.spinner(f"Analyzing via {provider}..."):
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
                trend.record_call(provider=provider, model=model, duration_ms=duration_ms, success=True, token_count=token_count)
                st.success(f"Complete ({duration_ms}ms, {token_count} tokens)")
                if snapshot:
                    st.markdown(f'<div class="glass-card"><div class="metric-label">Live Data</div><pre style="font-size:0.75rem;">{snapshot}</pre></div>', unsafe_allow_html=True)
                if macro and "No data" not in macro and "Could not" not in macro:
                    st.markdown(f'<div class="glass-card"><div class="metric-label">Macroeconomic Context</div><pre style="font-size:0.75rem;">{macro}</pre></div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="glass-card">'
                    f'<div class="metric-label">{ticker.upper()} Analysis</div>'
                    f'<div style="font-size:0.85rem;line-height:1.7;">{text}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
            except Exception as e:
                duration_ms = int((time.time() - start) * 1000)
                trend.record_call(provider=provider, model=model, duration_ms=duration_ms, success=False, error=str(e))
                st.error(f"Analysis failed: {e}")


def render_backtest_panel():
    st.markdown('<div class="section-title">\u2699\ufe0f Backtest</div>', unsafe_allow_html=True)

    results_dir = Path("~/.trading/backtest_results").expanduser()
    results_dir.mkdir(parents=True, exist_ok=True)
    result_files = sorted(results_dir.glob("*.json"), reverse=True)

    col_left, col_right = st.columns([1, 1.6])

    with col_left:
        st.markdown('<div class="glass-card" style="padding:1rem;">', unsafe_allow_html=True)
        bt_ticker = st.text_input("Ticker", value="AAPL", key="bt_ticker", placeholder="e.g. AAPL, MSFT")
        bt_from = st.text_input("Start", value="2020-01-01", key="bt_from")
        bt_to = st.text_input("End", value=datetime.now().strftime("%Y-%m-%d"), key="bt_to")
        bt_cash = st.number_input("Cash ($)", value=10_000, step=1_000, key="bt_cash")
        if st.button("Run Backtest", type="primary", key="bt_run", use_container_width=True):
            from trading.backtesting.midas import MIDAS
            with st.spinner(f"Running backtest for {bt_ticker.strip().upper()}..."):
                try:
                    engine = MIDAS(
                        initial_cash=float(bt_cash),
                        aegis_config={
                            "max_daily_drawdown": 0.50,
                            "max_trailing_drawdown": 0.75,
                            "max_position_pct": 1.0,
                            "max_positions": 10,
                        },
                    )
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
                    st.rerun()
                except Exception as e:
                    st.error(f"Backtest failed: {e}")
                    import traceback
                    st.code(traceback.format_exc(), language="python")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        bt_last = st.session_state.get("bt_last_result")
        if bt_last:
            m = bt_last["metrics"]
            tm = bt_last["trade_metrics"]
            eq = bt_last["equity"]

            rows = [
                ("Return", f'{m.get("total_return_pct", "?")}%', "pos" if float(m.get("total_return_pct", 0) or 0) >= 0 else "neg"),
                ("CAGR", f'{m.get("cagr_pct", "?")}%', "pos" if float(m.get("cagr_pct", 0) or 0) >= 0 else "neg"),
                ("Sharpe", str(m.get("sharpe_ratio", "?")), ""),
                ("Sortino", str(m.get("sortino_ratio", "?")), ""),
                ("Max DD", f'{m.get("max_drawdown_pct", "?")}%', "neg"),
                ("Volatility", f'{m.get("volatility_pct", "?")}%', ""),
                ("Trades", str(tm.get("num_trades", 0)), ""),
                ("Win Rate", f'{tm.get("win_rate", 0)}%', "pos"),
                ("Profit Factor", str(tm.get("profit_factor", 0)), ""),
                ("Total P&L", f'${tm.get("total_pnl", 0):,.2f}', "pos" if tm.get("total_pnl", 0) >= 0 else "neg"),
                ("Avg Win", f'${tm.get("avg_win", 0):,.2f}', "pos"),
                ("Avg Loss", f'${tm.get("avg_loss", 0):,.2f}', "neg"),
                ("Final Value", f'${m.get("final_value", 0):,.0f}', "gold"),
            ]
            rows_html = ""
            for i, (label, val, cls) in enumerate(rows):
                rows_html += f'<div class="data-row" style="animation-delay:{i*0.02}s;"><span class="label">{label}</span><span class="value {cls}">{val}</span></div>'

            st.markdown(
                f"""
                <div class="glass-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                        <span style="font-size:0.9rem;font-weight:700;color:#d4a843;font-family:'JetBrains Mono',monospace;">
                            {bt_last['ticker']}
                        </span>
                        <span style="font-size:0.65rem;color:#606070;font-family:'JetBrains Mono',monospace;">
                            {bt_last["from"]} \u2192 {bt_last["to"]}  |  {bt_last["steps"]} periods
                        </span>
                    </div>
                    {rows_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

            if len(eq) > 1:
                chart_data = pd.DataFrame({"equity": eq})
                st.line_chart(chart_data, height=240)

            with st.expander("Raw Data"):
                st.json(bt_last)

        elif result_files:
            selected = st.selectbox("Saved result", [f.name for f in result_files])
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
                        rows = [
                            ("Return", f'{metrics.get("total_return_pct", "?")}%', "pos" if float(metrics.get("total_return_pct", 0) or 0) >= 0 else "neg"),
                            ("CAGR", f'{metrics.get("cagr_pct", "?")}%', "pos" if float(metrics.get("cagr_pct", 0) or 0) >= 0 else "neg"),
                            ("Sharpe", str(metrics.get("sharpe_ratio", "?")), ""),
                            ("Sortino", str(metrics.get("sortino_ratio", "?")), ""),
                            ("Max DD", f'{metrics.get("max_drawdown_pct", "?")}%', "neg"),
                            ("Volatility", f'{metrics.get("volatility_pct", "?")}%', ""),
                            ("Trades", str(trade_met.get("num_trades", 0)), ""),
                            ("Win Rate", f'{trade_met.get("win_rate", 0)}%', "pos"),
                            ("Profit Factor", str(trade_met.get("profit_factor", 0)), ""),
                            ("Total P&L", f'${trade_met.get("total_pnl", 0):,.2f}', "pos" if trade_met.get("total_pnl", 0) >= 0 else "neg"),
                            ("Final Value", f'${metrics.get("final_value", 0):,.0f}', "gold"),
                        ]
                        rows_html = ""
                        for i, (label, val, cls) in enumerate(rows):
                            rows_html += f'<div class="data-row" style="animation-delay:{i*0.02}s;"><span class="label">{label}</span><span class="value {cls}">{val}</span></div>'
                        st.markdown(
                            f"""
                            <div class="glass-card">
                                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                                    <span style="font-size:0.9rem;font-weight:700;color:#d4a843;font-family:'JetBrains Mono',monospace;">
                                        {data.get("ticker", "?")}
                                    </span>
                                    <span style="font-size:0.65rem;color:#606070;font-family:'JetBrains Mono',monospace;">
                                        {data.get("start_date", "?")} \u2192 {data.get("end_date", "?")}
                                    </span>
                                </div>
                                {rows_html}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        if len(equity) > 1:
                            st.line_chart(pd.DataFrame({"equity": equity}), height=240)
                        with st.expander("Raw Data"):
                            st.json(data)
                except (json.JSONDecodeError, KeyError) as e:
                    st.error(f"Failed to load: {e}")
        else:
            st.markdown(
                '<div class="glass-card" style="text-align:center;padding:2rem;"><span style="color:#606070;font-size:0.85rem;">Run a backtest to see results here</span></div>',
                unsafe_allow_html=True,
            )


def render_portfolio_panel(arcane: Optional[ARCANE]):
    st.markdown('<div class="section-title">Portfolio</div>', unsafe_allow_html=True)
    if not arcane:
        st.info("No portfolio data loaded")
        return
    metrics = arcane.get_performance_metrics()
    rows = [
        ("Total Value", f"${metrics.get('total_value', 0):,.0f}", "gold"),
        ("Cash", f"${metrics.get('cash', 0):,.0f}", ""),
        ("Positions Value", f"${metrics.get('positions_value', 0):,.0f}", ""),
        ("Return", f"{metrics.get('total_return_pct', 0)}%", "pos" if metrics.get('total_return_pct', 0) >= 0 else "neg"),
        ("Drawdown", f"{metrics.get('trailing_drawdown', 0)*100:.1f}%", "neg"),
        ("Peak Value", f"${metrics.get('peak_value', 0):,.0f}", ""),
        ("Trade Count", str(metrics.get("trade_count", 0)), ""),
    ]
    rows_html = ""
    for label, val, cls in rows:
        rows_html += f'<div class="data-row"><span class="label">{label}</span><span class="value {cls}">{val}</span></div>'
    st.markdown(f'<div class="glass-card">{rows_html}</div>', unsafe_allow_html=True)


def render_provider_panel(trend: TREND):
    st.markdown('<div class="section-title">Provider Health</div>', unsafe_allow_html=True)
    try:
        summary = trend.get_summary()
    except Exception:
        st.warning("Provider health data unavailable")
        return
    provider_stats = summary.get("provider_stats", []) if isinstance(summary, dict) else []
    if not provider_stats:
        st.info("No provider data yet.")
        return
    rows_html = ""
    for stat in provider_stats:
        is_active = stat.get("provider", "") == summary.get("current_provider", "")
        prov_name = stat.get("provider", "?").upper() if isinstance(stat, dict) else "?"
        calls = stat.get("calls", 0) if isinstance(stat, dict) else 0
        sr = stat.get("success_rate", 0.0) if isinstance(stat, dict) else 0.0
        avg = stat.get("avg_duration_ms", 0) if isinstance(stat, dict) else 0
        toks = stat.get("total_tokens", 0) if isinstance(stat, dict) else 0
        pct = f"{sr * 100:.0f}%" if isinstance(sr, (int, float)) else "0%"
        avg_ms = f"{avg:.0f}ms" if isinstance(avg, (int, float)) else "0ms"
        dot_cls = "active" if is_active else "inactive"
        label = "ACTIVE" if is_active else "STANDBY"
        rows_html += f"""
        <div class="data-row">
            <span><span class="led-dot {dot_cls}"></span><span class="label">{prov_name}</span> <span style="color:#606070;font-size:0.6rem;">({label})</span></span>
            <span class="value">{calls} calls | {pct} | {avg_ms} | {toks} tok</span>
        </div>
        """
    st.markdown(f'<div class="glass-card">{rows_html}</div>', unsafe_allow_html=True)


def render_live_panel():
    st.markdown('<div class="section-title">Live Trading</div>', unsafe_allow_html=True)
    state_path = Path("~/.trading/live_state.json").expanduser()
    if not state_path.exists():
        st.info("No live trading data. Run `trading run AAPL` to start.")
        return
    try:
        data = json.loads(state_path.read_text())
        pv = data.get("portfolio_value", 0)
        cash = data.get("cash", 0)
        orders = data.get("orders", 0)
        positions = data.get("positions", [])
        rows = [
            ("Portfolio Value", f"${pv:,.0f}", "gold"),
            ("Cash", f"${cash:,.0f}", ""),
            ("Orders Filled", str(orders), ""),
            ("Open Positions", str(len(positions)), ""),
        ]
        rows_html = ""
        for label, val, cls in rows:
            rows_html += f'<div class="data-row"><span class="label">{label}</span><span class="value {cls}">{val}</span></div>'
        st.markdown(f'<div class="glass-card">{rows_html}</div>', unsafe_allow_html=True)
        if positions:
            pos_df = pd.DataFrame(positions)
            st.dataframe(pos_df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Failed to load live state: {e}")


def render_calls_panel(trend: TREND):
    st.markdown('<div class="section-title">Recent LLM Calls</div>', unsafe_allow_html=True)
    records = trend.records[-20:][::-1]
    if not records:
        st.info("No LLM calls recorded yet")
        return
    data = [
        {
            "Time": r.timestamp[-19:-7] if len(r.timestamp) > 19 else r.timestamp,
            "Provider": r.provider,
            "Model": r.model,
            "Status": "\u2705" if r.success else "\u274c",
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

    try:
        arcane = load_portfolio()
    except Exception:
        arcane = None

    st.markdown(KITCO_CSS, unsafe_allow_html=True)

    render_ticker_tape()

    now = datetime.now()
    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:center;padding:0.3rem 0 0.5rem 0;">
            <div style="display:flex;align-items:center;gap:0.8rem;">
                <span style="font-size:1.3rem;font-weight:700;color:#d4a843;letter-spacing:-0.5px;">T.R.E.N.D.</span>
                <span style="font-size:0.6rem;color:#606070;background:rgba(255,255,255,0.04);padding:0.15rem 0.5rem;border-radius:4px;font-family:'JetBrains Mono',monospace;">v2.1</span>
                <span class="led-dot gold" style="width:6px;height:6px;"></span>
                <span style="font-size:0.7rem;color:#606070;font-family:'JetBrains Mono',monospace;">{now.strftime('%Y-%m-%d %H:%M:%S')} UTC{now.astimezone().strftime('%z')}</span>
            </div>
            <div style="display:flex;gap:1.5rem;font-size:0.7rem;color:#606070;font-family:'JetBrains Mono',monospace;">
                <span>Contracts: 0</span>
                <span>Margin: 0%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_hero(arcane)

    with st.sidebar:
        st.markdown(
            '<div style="padding:0.8rem 0;"><span style="font-size:1rem;font-weight:700;color:#d4a843;">T.R.E.N.D.</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown("### Configuration")
        available = _detect_available_providers()
        if available:
            for prov, model in available:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:0.4rem;font-size:0.8rem;padding:0.2rem 0;">'
                    f'<span class="led-dot active" style="width:6px;height:6px;"></span>'
                    f'<span style="color:#b0b0bc;">{prov.upper()} ({model})</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.warning("No API keys configured")
        if "ticker_universe" in st.session_state:
            count = len(st.session_state.ticker_universe)
            ticker_str = f"{count:,} tickers loaded"
            if count > 10000:
                ticker_str += " (US + EU + IN)"
            st.caption(ticker_str)
        st.divider()
        st.markdown("### Quickstart")
        st.code("trading analyze AAPL")
        st.code("trading run AAPL --loop")
        st.code("trading backtest AAPL --from 2020-01-01")
        st.markdown(
            '<div style="margin-top:1rem;font-size:0.7rem;color:#606070;display:flex;gap:1rem;">'
            '<a href="https://github.com/gauravsengar24/SuperPower" style="color:#606070;text-decoration:none;">GitHub</a>'
            ' \u2022 '
            '<a href="https://github.com/gauravsengar24/SuperPower/blob/main/TRADING.md" style="color:#606070;text-decoration:none;">Docs</a>'
            "</div>",
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        render_backtest_panel()

    with col2:
        render_analysis_panel(trend)

    col3, col4, col5 = st.columns([1, 1, 1], gap="large")

    with col3:
        render_portfolio_panel(arcane)

    with col4:
        render_live_panel()

    with col5:
        render_provider_panel(trend)

    render_calls_panel(trend)

    with contextlib.suppress(Exception):
        save_trend_state(trend)


if __name__ == "__main__":
    run_dashboard()
