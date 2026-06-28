from __future__ import annotations

"""TradingMemoryLog — Append-only markdown decision log with rotation."""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TradingMemoryLog:
    """Append-only decision log stored as markdown.

    Stores: ticker, date, decision, outcome reflection
    Resolved entries are pruned when memory_log_max_entries is set.
    """

    def __init__(self, config: dict):
        self.config = config
        self.log_path = Path(config.get("memory_log_path", "~/.trading/memory/trading_memory.md")).expanduser()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.write_text("# Trading Memory Log\n\n")

    def store_decision(self, ticker: str, trade_date: str, final_trade_decision: str):
        entry = (
            f"## {ticker} | {trade_date}\n"
            f"- **Decision**: {final_trade_decision}\n"
            f"- **Status**: PENDING\n"
            f"- **Logged**: {datetime.now(timezone.utc).isoformat()}\n\n"
        )
        with open(self.log_path, "a") as f:
            f.write(entry)

    def get_past_context(self, ticker: str, max_entries: int = 5) -> str:
        """Get past context for the portfolio manager."""
        entries = self._parse_entries()
        ticker_entries = [e for e in entries if e.get("ticker", "").upper() == ticker.upper()]
        if not ticker_entries:
            return ""
        recent = ticker_entries[-max_entries:]
        lines = ["### Past Trading Decisions\n"]
        for e in recent:
            lines.append(f"- {e.get('date', '?')}: {e.get('decision', '?')} → {e.get('outcome', 'PENDING')}")
        return "\n".join(lines)

    def get_pending_entries(self) -> list[dict]:
        entries = self._parse_entries()
        return [e for e in entries if e.get("status", "").upper() == "PENDING"]

    def batch_update_with_outcomes(self, updates: list[dict]):
        content = self.log_path.read_text()
        for update in updates:
            marker = f"## {update['ticker']} | {update['trade_date']}"
            old = f"{marker}\n- **Decision**: {update.get('decision', '')}\n- **Status**: PENDING"
            new = (
                f"{marker}\n- **Decision**: {update.get('decision', '')}\n"
                f"- **Status**: RESOLVED\n"
                f"- **Raw Return**: {update.get('raw_return', 'N/A'):.4f}\n"
                f"- **Alpha**: {update.get('alpha_return', 'N/A'):.4f}\n"
                f"- **Reflection**: {update.get('reflection', 'N/A')}"
            )
            content = content.replace(old, new)
        self.log_path.write_text(content)
        self._apply_rotation()

    def _apply_rotation(self):
        max_entries = self.config.get("memory_log_max_entries")
        if max_entries is None:
            return
        entries = self._parse_entries()
        resolved = [e for e in entries if e.get("status", "").upper() != "PENDING"]
        if len(resolved) > max_entries:
            to_keep = len(entries) - (len(resolved) - max_entries)
            content = self.log_path.read_text()
            lines = content.split("\n")
            header = lines[:3]
            kept = "\n".join(header + lines[3:][-to_keep * 4:])
            self.log_path.write_text(kept)

    def _parse_entries(self) -> list[dict]:
        content = self.log_path.read_text()
        entries = []
        current = {}
        for line in content.split("\n"):
            if line.startswith("## "):
                if current:
                    entries.append(current)
                parts = line.replace("## ", "").split(" | ")
                current = {"ticker": parts[0].strip(), "date": parts[1].strip() if len(parts) > 1 else ""}
            elif line.startswith("- **Decision**"):
                current["decision"] = line.split(": ", 1)[1] if ": " in line else ""
            elif line.startswith("- **Status**"):
                current["status"] = line.split(": ", 1)[1] if ": " in line else ""
            elif line.startswith("- **Raw Return**"):
                current["outcome"] = line.split(": ", 1)[1] if ": " in line else ""
        if current:
            entries.append(current)
        return entries
