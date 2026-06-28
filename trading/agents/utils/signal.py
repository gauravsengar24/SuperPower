from __future__ import annotations

"""Signal processing — extract clean ratings from raw LLM output."""

import re
from typing import Any


_RATING_PATTERNS = [
    re.compile(r"(STRONG\s*BUY|BUY|SELL|STRONG\s*SELL|HOLD)", re.IGNORECASE),
    re.compile(r'"rating"\s*:\s*"([^"]+)"', re.IGNORECASE),
    re.compile(r'"signal"\s*:\s*"([^"]+)"', re.IGNORECASE),
    re.compile(r"rating[:\s]+(\w+)", re.IGNORECASE),
]


def parse_rating(text: str) -> str:
    """Extract the 5-tier rating from a text string."""
    if not text:
        return "HOLD"
    text_upper = text.upper()
    for pattern in _RATING_PATTERNS:
        match = pattern.search(text_upper)
        if match:
            raw = match.group(1).strip()
            normalized = raw.replace(" ", "_")
            if normalized in ("STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"):
                return normalized
    return "HOLD"


class SignalProcessor:
    def __init__(self, llm: Any | None = None):
        self.llm = llm

    def process_signal(self, raw_signal: str) -> str:
        return parse_rating(raw_signal)
