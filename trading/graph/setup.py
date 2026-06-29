"""Multi-stage pipeline: analysts → bull/bear debate → researcher → trader → portfolio manager → risk manager → decision."""

import logging

from trading.agents.utils.agent_utils import (
    get_instrument_context_from_state,
    get_language_instruction,
)

logger = logging.getLogger(__name__)

ANALYST_MARKET = "market"
ANALYST_SOCIAL = "social"
ANALYST_NEWS = "news"
ANALYST_FUNDAMENTALS = "fundamentals"


def run_simple_analyst_chain(state, selected_analysts, quick_llm, deep_llm, tool_nodes):
    """Run analysts in sequence, then debate → research → trade → portfolio manager → risk → decision."""
    trade_date = state.get("trade_date", "")
    ticker = state.get("company_of_interest", "UNKNOWN")
    instrument = get_instrument_context_from_state(state)
    lang = get_language_instruction(state.get("config", {}))

    for analyst_key in selected_analysts:
        if analyst_key == ANALYST_MARKET:
            from trading.agents.analysts.market_analyst import run_market_analyst
            report = run_market_analyst(ticker, trade_date, instrument, lang, quick_llm, tool_nodes)
            state["market_report"] = report
        elif analyst_key == ANALYST_SOCIAL:
            from trading.agents.analysts.sentiment_analyst import run_sentiment_analyst
            report = run_sentiment_analyst(ticker, trade_date, instrument, lang, quick_llm, tool_nodes)
            state["sentiment_report"] = str(report)
        elif analyst_key == ANALYST_NEWS:
            from trading.agents.analysts.news_analyst import run_news_analyst
            report = run_news_analyst(ticker, trade_date, instrument, lang, quick_llm)
            state["news_report"] = report
        elif analyst_key == ANALYST_FUNDAMENTALS:
            from trading.agents.analysts.fundamentals_analyst import run_fundamentals_analyst
            report = run_fundamentals_analyst(ticker, instrument, lang, deep_llm)
            state["fundamentals_report"] = report

    config = state.get("config", {})
    max_debate_rounds = int(config.get("max_debate_rounds", 1)) if isinstance(config, dict) else 1

    from trading.agents.researchers.debate import run_debate_researcher
    research_plan = run_debate_researcher(
        ticker, instrument, lang, deep_llm, quick_llm,
        market_report=state.get("market_report", ""),
        sentiment_report=state.get("sentiment_report", ""),
        news_report=state.get("news_report", ""),
        fundamentals_report=state.get("fundamentals_report", ""),
        max_rounds=max_debate_rounds,
    )
    state["investment_plan"] = research_plan

    from trading.agents.trader.trader import run_trader
    trader_proposal = run_trader(
        ticker, instrument, lang, quick_llm,
        research_plan=research_plan,
        market_report=state.get("market_report", ""),
        sentiment_report=state.get("sentiment_report", ""),
    )
    state["trader_investment_plan"] = trader_proposal

    from trading.agents.managers.portfolio_manager import run_portfolio_manager
    portfolio_decision = run_portfolio_manager(
        ticker, instrument, lang, deep_llm,
        research_plan=research_plan,
        trader_proposal=trader_proposal,
        market_report=state.get("market_report", ""),
        news_report=state.get("news_report", ""),
        fundamentals_report=state.get("fundamentals_report", ""),
    )
    state["portfolio_decision"] = portfolio_decision

    from trading.agents.risk_mgmt.risk_manager import run_risk_manager
    final_decision = run_risk_manager(
        ticker, trader_proposal=trader_proposal,
        aegis_config=config,
    )
    combined = portfolio_decision.approved and final_decision.approved
    state["final_trade_decision"] = "APPROVED" if combined else "REJECTED"

    return state
