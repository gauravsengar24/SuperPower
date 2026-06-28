---
name: trading-backtest
description: Use when the user wants to backtest a trading strategy across a historical date window using MIDAS
---

# Trading Backtest

Guide the user through running and interpreting a backtest with `trading backtest`.

## Quickstart

```
trading backtest AAPL --from 2020-01-01  # defaults to present
```

## The Process

### Step 1: Configure Parameters
Ask the user for:
- **Ticker** — symbol to backtest
- **Date range** — start and end dates (YYYY-MM-DD)
- **Interval** — days between analysis steps (default 30)
- **Initial cash** — starting portfolio value (default $100,000)
- **Risk per trade** — percentage of cash risked per trade (default 2%)
- **Max positions** — AEGIS hard limit (default 10)

### Step 2: Run Backtest
```bash
trading backtest {TICKER} \\
  --from {START_DATE} --to {END_DATE} \\
  --interval {DAYS} --cash {AMOUNT} \\
  --risk-per-trade {PCT} --max-positions {N}
```

### Step 3: Interpret Results
Present the output in this structure:

**Performance**
| Metric | What It Means |
|--------|---------------|
| Total Return | Overall P&L % over the full period |
| CAGR | Compound annual growth rate |
| Sharpe Ratio | Risk-adjusted return (>1 good, >2 excellent) |
| Sortino Ratio | Downside-risk-adjusted return |
| Max Drawdown | Largest peak-to-trough decline |
| Volatility | Annualized return standard deviation |

**Trades**
| Metric | What It Means |
|--------|---------------|
| Total Trades | Number of round-trip trades executed |
| Win Rate | % of profitable trades |
| Profit Factor | Gross profit / gross loss (>1.5 good) |
| Avg Win/Loss | Average $ amounts |

### Step 4: Sensitivity Analysis
Guide the user to try different parameters:
- Shorter intervals (7-14d) vs longer (60-90d)
- Higher/lower risk per trade (1% vs 5%)
- Different date ranges (bull vs bear markets)

Run comparison:
```bash
trading backtest {TICKER} --from 2022-01-01 --to 2022-12-31 --interval 14 --risk-per-trade 0.01
trading backtest {TICKER} --from 2022-01-01 --to 2022-12-31 --interval 14 --risk-per-trade 0.05
```

### Step 5: Launch Dashboard
```bash
trading dashboard
```
View the equity curve under the Backtest Viewer section.
