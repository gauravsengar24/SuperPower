from __future__ import annotations

import logging

from trading.agents.schemas import PortfolioDecision
from trading.risk.aegis import AEGIS, TradeProposal, PortfolioState, MarketSnapshot

logger = logging.getLogger(__name__)


def run_risk_manager(ticker, trader_proposal=None, aegis_config=None,
                     portfolio_state=None, market_snapshot=None):
    if not trader_proposal or trader_proposal.side == "HOLD":
        return PortfolioDecision(
            approved=False, risk_notes="No active trade proposal to evaluate",
            final_verdict="REJECTED",
        )

    aegis = AEGIS(aegis_config or {})

    proposal = TradeProposal(
        ticker=ticker,
        side=trader_proposal.side.lower(),
        qty=float(trader_proposal.quantity),
        order_type=trader_proposal.order_type.lower(),
        limit_price=trader_proposal.limit_price,
        stop_price=trader_proposal.stop_price,
        estimated_value=trader_proposal.quantity * (trader_proposal.limit_price or 100.0),
        confidence=trader_proposal.confidence_score,
    )

    ps = portfolio_state or PortfolioState(
        positions=[], cash=100000.0, total_value=100000.0,
        peak_value=100000.0, daily_start_value=100000.0,
        initial_value=100000.0,
    )
    ms = market_snapshot or MarketSnapshot(ticker=ticker, price=100.0, vix=15.0)

    all_pass, results = aegis.check(proposal, ps, ms)

    failed = [r for r in results if not r.passed]
    risk_notes = "; ".join(f"{r.gate_name}: {r.reason}" for r in failed) if failed else "All gates passed"

    if all_pass:
        return PortfolioDecision(
            approved=True, risk_notes=risk_notes,
            final_verdict="APPROVED",
        )
    else:
        return PortfolioDecision(
            approved=False,
            position_size_modification=None,
            risk_notes=risk_notes,
            final_verdict="REJECTED",
        )
