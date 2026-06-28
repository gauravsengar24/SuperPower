from __future__ import annotations

"""T.R.E.N.D. — Tactical Rick-Evaluation and Network Directed-trading.

Monitors LLM provider health, detects drift in agent outputs,
tracks response times, and manages automatic provider fallback.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import mean, stdev
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class LLMCallRecord:
    provider: str
    model: str
    duration_ms: float
    success: bool
    token_count: int = 0
    error: str = ""
    timestamp: str = ""


class TREND:
    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.records: list[LLMCallRecord] = []
        self.fallback_chain: list[str] = self.config.get(
            "provider_fallback_chain",
            ["openai", "anthropic", "google", "deepseek"],
        )
        self.current_provider_idx = 0
        self.error_threshold = self.config.get("error_threshold", 3)
        self.timeout_ms = self.config.get("timeout_ms", 60_000)
        self._provider_errors: dict[str, int] = defaultdict(int)

    @property
    def current_provider(self) -> str:
        return self.fallback_chain[self.current_provider_idx]

    def record_call(self, provider: str, model: str, duration_ms: float,
                    success: bool, token_count: int = 0, error: str = ""):
        record = LLMCallRecord(
            provider=provider,
            model=model,
            duration_ms=duration_ms,
            success=success,
            token_count=token_count,
            error=error,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self.records.append(record)
        if not success:
            self._provider_errors[provider] += 1
            if self._provider_errors[provider] >= self.error_threshold:
                self._maybe_fallback(provider)
        else:
            self._provider_errors[provider] = max(0, self._provider_errors[provider] - 1)

    def _maybe_fallback(self, failed_provider: str):
        if failed_provider == self.current_provider:
            next_idx = self.current_provider_idx + 1
            if next_idx < len(self.fallback_chain):
                logger.warning(
                    "TREND fallback: %s \u2192 %s (after %d errors)",
                    failed_provider,
                    self.fallback_chain[next_idx],
                    self.error_threshold,
                )
                self.current_provider_idx = next_idx
            else:
                logger.error("TREND: all providers exhausted!")
                self.current_provider_idx = 0

    def get_provider_stats(self, provider: str) -> dict:
        prov_records = [r for r in self.records if r.provider == provider]
        if not prov_records:
            return {"provider": provider, "calls": 0}
        durations = [r.duration_ms for r in prov_records]
        successes = sum(1 for r in prov_records if r.success)
        return {
            "provider": provider,
            "calls": len(prov_records),
            "success_rate": successes / len(prov_records) if prov_records else 0,
            "avg_duration_ms": mean(durations),
            "max_duration_ms": max(durations),
            "total_tokens": sum(r.token_count for r in prov_records),
        }

    def get_summary(self) -> dict:
        return {
            "current_provider": self.current_provider,
            "fallback_chain": self.fallback_chain,
            "total_calls": len(self.records),
            "total_errors": sum(1 for r in self.records if not r.success),
            "provider_stats": [
                self.get_provider_stats(p) for p in self.fallback_chain
            ],
        }
