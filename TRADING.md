# SuperTrading AI — Multi-Agent Trading Platform

> **Umbrella**: A.R.C.A.N.E. Trading Intelligence Systems  
> **Repo**: https://github.com/gauravsengar24/SuperPower  
> **Author**: [@gauravsengar24](https://github.com/gauravsengar24)

---

## The Bots

| Bot | Role | Status |
|-----|------|--------|
| **M.A.T.R.I.X.** | Multi-agent analysis orchestration (fka TradingAgents core) | ✅ Ported |
| **A.E.G.I.S.** | Hard risk gates — circuit breakers, VaR, position limits | 🔧 In progress |
| **V.E.L.O.C.I.T.Y.** | Real-time execution engine — broker routing, OMS | 🚧 Planned |
| **A.R.C.A.N.E.** | Portfolio management — P&L tracking, allocation, rebalancing | 🚧 Planned |
| **R.A.P.T.O.R.** | Market data feeds — WebSocket + REST | 🚧 Planned |
| **M.I.D.A.S.** | Backtesting — walk-forward, parameter optimization | 🚧 Planned |
| **H.E.R.M.E.S.** | Paper trading bridge | 🚧 Planned |
| **S.I.G.M.A.** | Signal processing + test coverage | ✅ Ported |
| **Q.U.A.N.T.** | LLM provider routing — cost-optimized model dispatch | ✅ Ported |
| **J.A.N.U.S.** | Dashboard — real-time P&L, decisions, risk state | 🚧 Planned |
| **P.L.U.T.O.** | CI/CD — GitHub Actions, Docker, deployment | 🔧 In progress |

---

## Architecture

```
┌──────────────────────────────────────────────┐
│         D E V E L O P M E N T  L A Y E R      │
│  ┌──────────┐ ┌───────────┐ ┌──────────────┐ │
│  │Brainstorm│ │TDD+BACKTEST│ │  Code Review │ │
│  └──────────┘ └───────────┘ └──────────────┘ │
├──────────────────────────────────────────────┤
│         A N A L Y S I S  L A Y E R            │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │ Analysts │ │Researcher│ │    Trader     │ │
│  │ (4 types)│ │Bull/Bear │ │  (Proposal)  │ │
│  └──────────┘ └──────────┘ └──────────────┘ │
├──────────────────────────────────────────────┤
│         R I S K  L A Y E R  (A.E.G.I.S.)      │
│  ┌─────────┐ ┌───────────┐ ┌──────────────┐ │
│  │Hard Gates│ │Position   │ │Circuit       │ │
│  │         │ │Sizing     │ │Breakers      │ │
│  └─────────┘ └───────────┘ └──────────────┘ │
├──────────────────────────────────────────────┤
│       E X E C U T I O N  L A Y E R           │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │Paper     │ │Broker API│ │Order Mgmt    │ │
│  │Trading   │ │Alpaca/IBK│ │System (OMS)  │ │
│  └──────────┘ └──────────┘ └──────────────┘ │
├──────────────────────────────────────────────┤
│       P O R T F O L I O  L A Y E R           │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
│  │P&L       │ │Allocation│ │  Dashboard   │ │
│  │Tracker   │ │Mgmt     │ │  (Streamlit)│ │
│  └──────────┘ └──────────┘ └──────────────┘ │
└──────────────────────────────────────────────┘
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/gauravsengar24/SuperPower.git
cd SuperPower

# 2. Install trading system
pip install -e trading/

# 3. Set up API keys (copy .env.example → .env)
cp .env.example .env

# 4. Analyze a ticker
trading --ticker AAPL --date 2026-01-15

# 5. Launch dashboard
trading dashboard
```

---

## Project Structure

```
trading/
├── agents/                   # Multi-agent analysis (ported from TradingAgents)
│   ├── analysts/             # Market, Sentiment, News, Fundamentals
│   ├── researchers/          # Bull + Bear debate
│   ├── managers/             # Research Manager + Portfolio Manager
│   ├── risk_mgmt/            # Aggressive, Conservative, Neutral debaters
│   ├── trader/               # Trade proposal generation
│   └── utils/                # Agent utilities, memory, signals
├── graph/                    # LangGraph pipeline orchestration
├── dataflows/                # Data vendor abstraction (yfinance, AV, FRED, etc.)
├── llm_clients/              # Multi-provider LLM factory (14+ providers)
├── risk/                     # [A.E.G.I.S.] Hard risk gates
├── execution/                # [V.E.L.O.C.I.T.Y.] Order execution
├── broker/                   # Broker abstraction layer
├── data/                     # [R.A.P.T.O.R.] Market data feeds
├── portfolio/                # [A.R.C.A.N.E.] Portfolio tracking
├── backtesting/              # [M.I.D.A.S.] Backtest engine
├── monitoring/               # [J.A.N.U.S.] Model monitoring
├── cli/                      # Command-line interface
├── tests/                    # All tests
└── default_config.py         # Single source of config truth
```

---

## Roadmap

| Phase | What | Status |
|-------|------|--------|
| 1 | Deep analysis + architecture docs | ✅ Done |
| 2 | Bug fixes + test coverage (MATRIX + SIGMA) | ✅ Done — 12/12 interop tests, 7 bugs fixed |
| 3 | Hard risk gates (AEGIS) | ✅ Done — 5 gates in chain-of-responsibility |
| 4 | Execution engine (VELOCITY) | ✅ Done — paper + Alpaca adapters |
| 5 | Portfolio management (ARCANE) | ✅ Done — P&L, positions, metrics |
| 6 | Backtesting (MIDAS) | 📋 Planned |
| 7 | Dashboard + monitoring (JANUS) | ✅ Done — provider fallback + drift detection |
| 8 | Agent modules + test coverage | ✅ Done — 7 agent modules, 47 new tests (98 total) |
| 9 | SuperPower trading skills | 📋 Planned |

---

## Bug Tracker (From Phase 1 Audit)

| ID | Bug | Severity | Status |
|----|-----|----------|--------|
| B1 | `get_insider_transactions` not in `TOOLS_CATEGORIES` | 🔴 Critical | ✅ Fixed |
| B2 | LLM call counter doubled in StatsCallbackHandler | 🟠 Medium | ✅ Fixed |
| B3 | Global news stops after first query hits limit | 🟠 Medium | ✅ Fixed |
| B4 | Alpha Vantage historical data truncated | 🟠 Medium | ✅ Fixed |
| B5 | Fundamentals always uses quick-think LLM | 🟢 Low | ✅ Fixed |
| B6 | Sentiment analyst dead ToolNode | 🟢 Low | ✅ Fixed |
| B7 | Multiple `print()` in production code | 🟢 Low | ✅ Fixed |
| B8 | Polymarket return type mismatch | 🟠 Medium | ✅ Fixed |

---

## License

MIT — see [LICENSE](LICENSE)

Built on [obra/superpowers](https://github.com/obra/superpowers) × [TauricResearch/TradingAgents](https://github.com/tauricresearch/tradingagents)
