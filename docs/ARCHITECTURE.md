# SuperTrading AI — Architecture Documentation

**Author**: [@gauravsengar24](https://github.com/gauravsengar24)  
**Repo**: https://github.com/gauravsengar24/SuperPower  
**Last Updated**: 2026-06-29

---

## 1. System Overview

SuperTrading AI is a multi-agent AI trading platform built by merging two open-source projects:

- **SuperPower** (obra/superpowers v6.0.3) — AI coding agent development methodology
- **TradingAgents** (TauricResearch v0.3.0) — Multi-agent LLM financial trading framework

The merged system adds: hard risk gates, real-time execution, portfolio management, backtesting, and a monitoring dashboard — filling gaps in both upstream projects.

---

## 2. Agent Pipeline (MATRIX)

```
User Input: "Analyze AAPL on 2026-01-15"
         │
         ▼
┌───────────────────────┐
│ 1. Instrument Identity │  Deterministic yfinance lookup
│    Resolution          │  → company name, sector, industry
└─────────┬─────────────┘
          │
     ┌────▼──────────────┐
     │ 2. Analysts       │  Sequential (configurable order)
     │    ─────────────  │
     │ Market Analyst    │  OHLCV + 15 technical indicators
     │ Sentiment Analyst │  StockTwits + Reddit → structured
     │ News Analyst      │  Macro news + insider trades + Polymarket
     │ Fundamentals      │  Income, balance sheet, cash flow
     └────┬──────────────┘
          │
     ┌────▼──────────────┐
     │ 3. Researchers    │  Structured debate
     │    ─────────────  │  Bull ↔ Bear alternating
     │ Research Manager  │  → ResearchPlan (structured output)
     └────┬──────────────┘
          │
     ┌────▼──────────────┐
     │ 4. Trader         │  → TraderProposal (structured)
     │    (structured)   │  side, entry, stop, target, confidence
     └────┬──────────────┘
          │
     ┌────▼──────────────┐
     │ 5. Risk Debate    │  3-way: Aggressive ↔ Conservative ↔ Neutral
     │    ─────────────  │  → PortfolioManager → PortfolioDecision
     └────┬──────────────┘
          │
     ┌────▼──────────────┐
     │ 6. A.E.G.I.S.     │  HARD RISK GATES (no LLM)
     │    ─────────────  │  Position limits, VaR, drawdown, vol filter
     └────┬──────────────┘
          │
     ┌────▼──────────────┐
     │ 7. V.E.L.O.C.I.T.Y.│  Execution engine
     │    ─────────────  │  Paper → Live, OMS, fill monitoring
     └────┬──────────────┘
          │
     ┌────▼──────────────┐
     │ 8. A.R.C.A.N.E.   │  Portfolio update, P&L, memory log
     └───────────────────┘
```

---

## 3. Graph State (AgentState)

```python
class AgentState(TypedDict):
    # Identity
    company_of_interest: str
    trade_date: str
    asset_type: str
    
    # Past context (injected before pipeline)
    past_context: str
    instrument_context: str
    
    # Messages (LangGraph standard)
    messages: Sequence[BaseMessage]
    
    # Analyst reports
    market_report: str
    sentiment_report: str
    news_report: str
    fundamentals_report: str
    
    # Debate state
    investment_debate_state: InvestDebateState  # bull/bear histories
    risk_debate_state: RiskDebateState           # aggressive/conservative/neutral
    
    # Research + Trading
    investment_plan: ResearchPlan  # structured
    trader_investment_plan: str    # raw trader output
    
    # Final decision
    final_trade_decision: str  # raw output
```

---

## 4. Data Vendor Architecture

```
        ┌──────────────────────────────┐
        │       TOOL FUNCTIONS          │
        │  get_stock_data()             │
        │  get_indicators()             │
        │  get_fundamentals()           │
        │  get_news()                   │
        │  get_global_news()            │
        │  get_macro_indicators()       │
        │  get_prediction_markets()     │
        │  get_insider_transactions()   │
        └──────────┬───────────────────┘
                   │
        ┌──────────▼───────────────────┐
        │     route_to_vendor()         │
        │  (interface.py)              │
        │  Maps tool → vendor chain    │
        └──────────┬───────────────────┘
                   │
     ┌─────────────┼─────────────┐
     │             │             │
     ▼             ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ yfinance │ │Alpha Vant│ │  FRED    │
│ (free)   │ │(free tier)│ │ (free)  │
└──────────┘ └──────────┘ └──────────┘
     │             │             │
     ▼             ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│StockTwits│ │ Polymkt  │ │  Reddit  │
│ (free)   │ │ (free)   │ │  (free)  │
└──────────┘ └──────────┘ └──────────┘
```

Vendor routing is configurable via `data_vendors` in `default_config.py`:

```python
"data_vendors": {
    "core_stock_apis": "yfinance",        # or "alpha_vantage"
    "technical_indicators": "yfinance",
    "fundamental_data": "yfinance",
    "news_data": "yfinance",
    "macro_data": "fred",
    "prediction_markets": "polymarket",
}
```

---

## 5. LLM Provider Architecture (QUANT)

```
create_llm_client(provider, model, base_url, **kwargs)
         │
         ├── "openai"       → OpenAIClient
         ├── "anthropic"    → AnthropicClient
         ├── "google"       → GoogleClient
         ├── "deepseek"     → DeepSeekChatOpenAI
         ├── "azure"        → AzureOpenAIClient
         ├── "bedrock"      → BedrockClient (optional)
         ├── "ollama"       → LocalCompatibleChatOpenAI
         ├── "openai_compatible" → LocalCompatibleChatOpenAI
         └── 6+ others      → factory dispatch
```

Dual-model architecture:
- `deep_thinking_llm`: Complex reasoning (research manager, portfolio manager)
- `quick_thinking_llm`: Fast tasks (analysts, researchers, trader)

---

## 6. A.E.G.I.S. Risk Gate Architecture

```
TraderProposal from MATRIX
         │
    ┌────▼──────────────────────┐
    │ AEGIS.check(proposal,     │
    │        portfolio, market) │  Chain-of-responsibility
    ├───────────────────────────┤
    │ 1. PositionLimitGate     │  Max positions, max % per asset
    │ 2. DrawdownGate          │  Daily + trailing drawdown
    │ 3. VaRGate               │  Position VaR vs portfolio
    │ 4. VolatilityFilterGate  │  VIX / ATR regime check
    │ 5. CorrelationGate       │  Multi-asset correlation
    │ 6. OrderSizeGate         │  Kelly sizing validation
    └────┬──────────────────────┘
         │
    ┌────▼────────────┐
    │ PASS / REJECT   │  → VELOCITY (if PASS)
    └─────────────────┘           → AEGIS log (if REJECT)
```

All gates are **pure Python** — no LLM involvement. Deterministic, auditable, fast.

---

## 7. V.E.L.O.C.I.T.Y. Execution Architecture

```
Order from AEGIS
    │
    ▼
┌──────────────────┐
│ Order Validator  │  Check for NAN/infinite prices, zero qty
└──────┬───────────┘
       ▼
┌──────────────────┐
│ Broker Router    │  Paper → HermesPaperBroker
│                  │  Live   → AlpacaBroker / IBKRBroker
└──────┬───────────┘
       ▼
┌──────────────────┐
│ Order Manager    │  Track lifecycle: created→submitted→filled
│ (OMS)            │  →partial→cancelled→rejected
└──────┬───────────┘
       ▼
┌──────────────────┐
│ Fill Monitor     │  WebSocket fill listener
│                  │  → ARCANE portfolio update
└──────────────────┘
```

---

## 8. Broker Support

| Broker | Paper | Live | Pricing | Status |
|--------|-------|------|---------|--------|
| Alpaca | ✅ Free | ✅ Free | Free tier | 🚧 Planned |
| Interactive Brokers | ❌ | ✅ | Subscription | 🚧 Planned |
| Tradier | ✅ Free | ✅ | $10/mo | 🚧 Planned |

Design principle: **No per-query charges**. All APIs supported have subscription or free models, not per-request billing.

---

## 9. Memory & Persistence

```
~/.tradingagents/
├── memory/
│   └── trading_memory.md     # Append-only decision log
├── cache/
│   ├── checkpoints/          # SQLite per-ticker (opt-in)
│   │   ├── AAPL.db
│   │   └── SPY.db
│   └── data/                 # Cached OHLCV data
└── logs/
    └── reports/              # Markdown report trees
```

---

## 10. Known Bugs (From Audit)

See [Phase 1 Audit](BUGS.md) for full list.

| # | Component | Bug | Severity | Fix |
|---|-----------|-----|----------|-----|
| 1 | `interface.py` | `get_insider_transactions` missing from `TOOLS_CATEGORIES` | 🔴 | Add to `news_data` tools list |
| 2 | `cli/stats_handler.py` | LLM call count doubled | 🟠 | Remove `on_llm_start` handler |
| 3 | `yfinance_news.py` | Global news stops after 1st query | 🟠 | Collect all before truncating |

---

*For full documentation, visit https://github.com/gauravsengar24/SuperPower/tree/main/docs*
