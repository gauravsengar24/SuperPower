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

- **File**: `trading/cli/stats_handler.py` (ported)
- **Impact**: `StatsCallbackHandler` implements both `on_llm_start` and `on_chat_model_start`, which LangChain fires for the same chat model call — doubling the count
- **Fix**: Remove `on_llm_start` handler, keep only `on_chat_model_start`
- **Status**: ⏳ To be fixed

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
- **Status**: ⏳ Not yet fixed (requires Alpha Vantage module port)

---

## BUG-5 (Low): Fundamentals Always Uses Quick-Thinking LLM

- **File**: `trading/graph/setup.py`
- **Impact**: The fundamentals analyst — which requires the deepest reasoning — is assigned the quick model, while simpler tasks use the same model
- **Fix**: Changed fundamentals factory to use `deep_thinking_llm`
- **Status**: ✅ Fixed in ported codebase

---

## BUG-6 (Low): Sentiment Analyst Dead ToolNode

- **File**: `trading/graph/trading_graph.py`
- **Impact**: The `"social"` ToolNode includes tools, but the sentiment analyst never binds tools — the ToolNode is dead code
- **Status**: ⏳ To be fixed (tools vs no-tools design decision)

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
- **Status**: ⏳ Not yet fixed (requires Polymarket module port)

---

## BUG-9 (Low): SuperPower `task-brief` Quoting Bug

- **File**: `skills/subagent-driven-development/scripts/task-brief:23`
- **Impact**: `dir=$("$(cd "$(dirname "$0")" && pwd)/sdd-workspace")` constructs a path string instead of executing the `sdd-workspace` script. Breaks workspace resolution.
- **Fix**: Fix command substitution quoting
- **Status**: ⏳ To be fixed

---

## BUG-10 (Low): SuperPower `review-package` Quoting Bug

- **File**: `skills/subagent-driven-development/scripts/review-package:26`
- **Impact**: Same quoting bug as BUG-9
- **Fix**: Fix command substitution quoting
- **Status**: ⏳ To be fixed

---

## BUG-11 (Low): Kimi Plugin Truncated Instructions

- **File**: `.kimi-plugin/plugin.json:25`
- **Impact**: `skillInstructions` field is truncated at 2000 characters — Kimi agents receive incomplete instructions
- **Status**: ⏳ To be fixed

---

## BUG-12 (Low): Pre-Commit References Missing `evals/` Directory

- **File**: `.pre-commit-config.yaml:6`
- **Impact**: Runs `uv --project evals run ruff check` but `evals/` was removed in v6.0.2. Pre-commit fails for all users.
- **Fix**: Remove or gate the evals check
- **Status**: ⏳ To be fixed

---

## Testing Gaps

| Area | Coverage | Target |
|------|----------|--------|
| Agent logic (all 14 agents) | 0% | ≥80% |
| Graph setup and edges | 0% | ≥80% |
| Vendor routing | 0% | ≥80% |
| LLM client creation | 0% | ≥80% |
| CLI interactive flow | 0% | ≥60% |
| Alpha Vantage dataflows | 0% | ≥70% |
| StockTwits + Reddit dataflows | 0% | ≥70% |
| AEGIS risk gates | ✅ Newly written | ≥90% |
| Hermes paper broker | ✅ Newly written | ≥90% |
| ARCANE portfolio | ✅ Newly written | ≥90% |
| Signal processing | ✅ Newly written | ≥95% |
| VELOCITY execution | ✅ Newly written | ≥90% |

---

*Last updated: 2026-06-29*
