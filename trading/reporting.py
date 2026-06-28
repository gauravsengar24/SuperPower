from __future__ import annotations

"""Report tree writer — saves analysis results as markdown files."""

from datetime import datetime
from pathlib import Path
from typing import Any


def write_report_tree(final_state: dict, ticker: str, save_path: Path) -> Path:
    """Write the markdown report tree for a completed run."""
    save_path = Path(save_path)
    save_path.mkdir(parents=True, exist_ok=True)

    sections = {
        "summary": _summary_report(final_state, ticker),
        "market_analysis": final_state.get("market_report", "N/A"),
        "sentiment_analysis": final_state.get("sentiment_report", "N/A"),
        "news_analysis": final_state.get("news_report", "N/A"),
        "fundamentals_analysis": final_state.get("fundamentals_report", "N/A"),
        "final_decision": f"# Final Decision\n\n{final_state.get('final_trade_decision', 'N/A')}",
    }

    for name, content in sections.items():
        (save_path / f"{name}.md").write_text(content)

    # Write combined report
    combined = f"# Trading Analysis Report: {ticker}\n\n"
    combined += f"**Date**: {final_state.get('trade_date', 'N/A')}\n\n"
    for name, content in sections.items():
        combined += f"---\n\n## {name.replace('_', ' ').title()}\n\n{content}\n\n"
    (save_path / "report.md").write_text(combined)

    return save_path


def _summary_report(state: dict, ticker: str) -> str:
    return (
        f"# Analysis Summary: {ticker}\n\n"
        f"**Trade Date**: {state.get('trade_date', 'N/A')}\n"
        f"**Signal**: {state.get('final_trade_decision', 'N/A')[:50]}...\n"
        f"**Generated**: {datetime.now().isoformat()}\n"
    )
