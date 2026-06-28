# Bug Tracker — SuperTrading AI

All bugs identified during Phase 1 audit of the merged codebase.

---

## BUG-1 (Critical): `get_insider_transactions` not in `TOOLS_CATEGORIES`

- **File**: `trading/dataflows/interface.py` (ported from TradingAgents)
- **Impact**: Calling `get_category_for_method("get_insider_transactions")` raises `ValueError`
- **Root Cause**: Tool is wired into the news ToolNode in `trading_graph.py` but the method name is not registered in the `TOOLS_CATEGORIES` constant
- **Fix**: Add `"get_insider_transactions"` to `TOOLS_CATEGORIES["news_data"]["tools"]` in `interface.py`
- **Status**: ✅ Fixed in ported codebase

---

## BUG-2 (Medium): LLM Call Counter Double-Counted

- **File**: `trading/cli/stats_handler.py`
- **Impact**: `StatsCallbackHandler` implements both `on_llm_start` and `on_chat_model_start`, which LangChain fires for the same chat model call — doubling the count
- **Fix**: Remove `on_llm_start` handler, keep only `on_chat_model_start`
- **Status**: ✅ Fixed — handler created with only `on_chat_model_start`

---

## BUG-3 (Medium): Global News Stops After First Query

- **File**: `trading/dataflows/yfinance_news.py`
- **Impact**: The `get_global_news` loop contains `len(all_news) >= limit` check inside the loop body, causing early termination after the first query fills the limit. Later queries never contribute.
- **Fix**: Removed the early break — collect from ALL queries first, then truncate to limit
- **Status**: ✅ Fixed in ported codebase

---

## BUG-4 (Medium): Alpha Vantage Historical Data Truncation

- **File**: `trading/dataflows/alpha_vantage_stock.py`
- **Impact**: Uses `datetime.now()` instead of the analysis date to determine "compact" vs "full" data. For historical backtest dates, always returns "compact" (100 days) when analysis is within 100 days of today
- **Fix**: Use the requested analysis date instead of `datetime.now()` to determine outputsize
- **Status**: ✅ Fixed — uses `analysis_date` parameter, falls back to "full" when date is >90 days in the past

---

## BUG-5 (Low): Fundamentals Always Uses Quick-Thinking LLM

- **File**: `trading/graph/setup.py`
- **Impact**: The fundamentals analyst — which requires the deepest reasoning — is assigned the quick model, while simpler tasks use the same model
- **Fix**: Changed fundamentals factory to use `deep_thinking_llm`
- **Status**: ✅ Fixed in ported codebase

---

## BUG-6 (Low): Sentiment Analyst Dead ToolNode

- **File**: `trading/graph/trading_graph.py`, `trading/graph/setup.py`
- **Impact**: The `"social"` ToolNode includes tools, but the sentiment analyst never binds tools — the ToolNode is dead code
- **Fix**: Added `_run_sentiment_analyst` that calls LLM with tool context
- **Status**: ✅ Fixed — sentiment analyst now calls LLM with tools context

---

## BUG-7 (Low): `print()` Statements in Production Code

- **Files**: Multiple `dataflows/` files
- **Impact**: Debug `print()` calls in production dataflow code instead of proper logging
- **Fix**: Replace all with `logger.warning()` or `logger.info()`
- **Status**: ✅ Fixed in ported codebase

---

## BUG-8 (Medium): Polymarket Return Type Mismatch

- **File**: `trading/dataflows/polymarket.py`
- **Impact**: `_request` method return type annotated as `dict` but Gamma API can return `list` for some endpoints. Calling `.get("events", [])` on a list would crash.
- **Fix**: Handle both `dict` and `list` returns
- **Status**: ✅ Fixed — `_request` returns `dict | list`, consumers check type

---

## BUG-9 (Low): SuperPower `task-brief` Quoting Bug

- **File**: `skills/subagent-driven-development/scripts/task-brief:23`
- **Impact**: `dir=$("$(cd "$(dirname "$0")" && pwd)/sdd-workspace")` constructs a path string instead of executing the `sdd-workspace` script. Breaks workspace resolution.
- **Fix**: Fix command substitution quoting
- **Status**: ✅ Fixed — removed outer `$()` wrapping command substitution


---

## BUG-10 (Low): SuperPower `review-package` Quoting Bug

- **File**: `skills/subagent-driven-development/scripts/review-package:26`
- **Impact**: Same quoting bug as BUG-9
- **Fix**: Fix command substitution quoting
- **Status**: ✅ Fixed — same fix as BUG-9
---

## BUG-11 (Low): Kimi Plugin Truncated Instructions

- **File**: `.kimi-plugin/plugin.json:25`
- **Impact**: `skillInstructions` field is truncated at 2000 characters — Kimi agents receive incomplete instructions
- **Status**: ✅ Already within limit — content is 1961 chars, under 2000 char ceiling

---

## BUG-12 (Low): Pre-Commit References Missing `evals/` Directory

- **File**: `.pre-commit-config.yaml`
- **Impact**: Runs `uv --project evals run ruff check` but `evals/` was removed in v6.0.2. Pre-commit fails for all users.
- **Fix**: Remove or gate the evals check
- **Status**: ✅ Fixed — `evals/` reference removed, config now lints `trading/` only

---

## Testing Gaps

| Area | Tests | Target | Status |
|------|-------|--------|--------|
| Agent logic (sentiment, news, fundamentals, researcher, trader, risk mgr, portfolio mgr) | 32 | ≥80% | ✅ 32 tests written |
| Graph setup and edges | 6 | ≥80% | ✅ 6 tests written |
| Vendor routing | 0 | ≥80% | 📋 Planned (StockTwits, Reddit, FRED) |
| LLM client creation | 11 | ≥80% | ✅ 11 tests written |
| CLI interactive flow | 0 | ≥60% | 📋 Planned |
| Backtesting engine (MIDAS) | 17 | ≥80% | ✅ 17 tests written |
| Alpha Vantage dataflows | 3 | ≥70% | ✅ 3 tests (in interop suite) |
| StockTwits + Reddit dataflows | 0 | ≥70% | 📋 Planned (not ported) |
| AEGIS risk gates | 8 | ≥90% | ✅ Written |
| Hermes paper broker | 6 | ≥90% | ✅ Written |
| ARCANE portfolio | 6 | ≥90% | ✅ Written |
| Signal processing | 10 | ≥95% | ✅ Written |
| VELOCITY execution | 2 | ≥90% | ✅ Written |

---

*Last updated: 2026-06-29*
