"""Initial state creation for the graph pipeline."""


def create_initial_state(ticker, trade_date, asset_type="stock",
                         past_context="", instrument_context=""):
    return {
        "company_of_interest": ticker,
        "trade_date": str(trade_date),
        "asset_type": asset_type,
        "past_context": past_context,
        "instrument_context": instrument_context,
        "messages": [],
        "market_report": "",
        "sentiment_report": "",
        "news_report": "",
        "fundamentals_report": "",
        "investment_debate_state": {
            "bull_history": "",
            "bear_history": "",
            "history": "",
            "current_response": "",
            "judge_decision": "",
            "generation": 0,
        },
        "risk_debate_state": {
            "aggressive_history": "",
            "conservative_history": "",
            "neutral_history": "",
            "history": "",
            "judge_decision": "",
            "generation": 0,
        },
        "investment_plan": "",
        "trader_investment_plan": "",
        "final_trade_decision": "HOLD",
    }
