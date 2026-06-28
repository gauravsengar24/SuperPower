---
name: trading-portfolio-review
description: Use when the user asks about portfolio status, P&L, open positions, or risk exposure using ARCANE + TREND
---

# Trading Portfolio Review

Guide the user through reviewing portfolio status, positions, P&L, and risk exposure.

## Quickstart

```
trading portfolio
trading dashboard
```

## The Process

### Step 1: Show Portfolio Summary
```bash
trading portfolio
```

This displays:
- **Total Value** — current cash + positions value
- **Cash** — available buying power
- **Total Return** — P&L %
- **Positions Value** — market value of open positions
- **Num Positions** — count of open positions
- **Drawdown** — current trailing drawdown %
- **Trade Count** — total trades executed

### Step 2: Launch Dashboard for Visual View
```bash
trading dashboard
```
The TREND dashboard provides:
- **Provider Health** — LLM fallback status, call stats, latency
- **Portfolio Panel** — value, cash, return, drawdown cards
- **Backtest Viewer** — equity curves from past runs
- **Recent LLM Calls** — last 20 provider calls

### Step 3: Assess Risk Exposure
Review these risk metrics:
1. **Position concentration** — single ticker % of portfolio (AEGIS limit: 25%)
2. **Drawdown status** — daily drawdown (limit: 5%) + trailing drawdown (limit: 15%)
3. **Cash reserve** — % of portfolio in cash
4. **Volatility regime** — VIX level if available

### Step 4: Discuss Actions
Based on the review, suggest:
- Rebalance over-concentrated positions
- Reduce exposure if drawdown limits are near
- Increase cash reserve in high-volatility regimes
- Run fresh analysis on underperforming positions (`trading analyze {TICKER}`)

### Step 5: Risk Gate Configuration
To adjust AEGIS risk parameters:
```bash
export TRADING_MAX_POSITIONS=5
export TRADING_MAX_POSITION_PCT=0.15
export TRADING_MAX_DAILY_DRAWDOWN=0.03
export TRADING_DEFAULT_RISK_PER_TRADE=0.01
```
Run analysis with tighter gates:
```bash
trading analyze {TICKER} --date {DATE}
```
