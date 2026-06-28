---
name: trading-analysis
description: Use when the user wants to analyze a stock, crypto, or other ticker using the SuperTrading AI multi-agent pipeline (MATRIX)
---

# Trading Analysis

Guide the user through analyzing a ticker using `trading analyze`.

## Quickstart

```
trading analyze AAPL --date 2026-06-29
```

## The Process

### Step 1: Gather Context
- Ask the user: ticker symbol, date (defaults to today), and optional LLM provider override
- Present options: openai (default), anthropic, google, deepseek, groq, etc.

### Step 2: Run Analysis
```bash
trading analyze {TICKER} --date {DATE} --provider {PROVIDER}
```

### Step 3: Interpret Results
Present the output in this structure:
1. **Signal** — STRONG BUY / BUY / HOLD / SELL / STRONG SELL
2. **Market Analysis** — price action, trends, key levels
3. **Sentiment** — social media, news tone
4. **News/Macro** — headlines, macro conditions
5. **Fundamentals** — financial health, valuation
6. **Decision Summary** — final trade decision with reasoning

### Step 4: Discuss Next Steps
- Run a backtest (`trading backtest {TICKER} --from 2020-01-01` — defaults to present)
- Launch dashboard (`trading dashboard`)
- View portfolio (`trading portfolio`)
- Adjust risk parameters and re-run

## Multi-Ticker Analysis

For portfolio-wide scans:
```bash
for ticker in AAPL MSFT GOOGL TSLA AMZN; do
    trading analyze "$ticker" --date "$DATE"
done
```

## Environment Variables
- `OPENAI_API_KEY` — required for OpenAI provider
- `ANTHROPIC_API_KEY` — required for Anthropic
- `GOOGLE_API_KEY` — required for Google/Gemini
- See `.env.example` for full list
